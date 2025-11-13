
import hashlib
import subprocess
import sys
import os

def get_file_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def compare_file_with_remote(filename, remote_branch="origin/actualizacion-cursor"):
    local_hash = get_file_hash(filename)

    try:
        result = subprocess.run(
            ["git", "show", f"{remote_branch}:{filename}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=False
        )
        remote_hash = hashlib.sha256(result.stdout).hexdigest()
    except subprocess.CalledProcessError as e:
        print(f"❌ No se pudo obtener la versión remota de `{filename}`:")
        print(e.stderr.decode())
        return

    if not local_hash:
        print(f"❌ El archivo local `{filename}` no existe.")
    elif local_hash == remote_hash:
        print(f"✅ El archivo local `{filename}` está sincronizado con el remoto.")
    else:
        print(f"⚠️ El archivo local `{filename}` NO coincide con la versión remota.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python compare_with_remote.py <archivo>")
    else:
        compare_file_with_remote(sys.argv[1])
