
import subprocess
import sys
from pathlib import Path
import time
import tempfile
import logging

"""
# Installation des dépendances
sudo apt-get install -y libreoffice
pip install unoserver

# Vérification de l'installation
which unoserver  # Doit retourner /usr/local/bin/unoserver
unoconvert --version
"""

def install_libreoffice():
    try:
        # Mise à jour des paquets et installation
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        subprocess.run(
            ["sudo", "apt-get", "install", "-y", "libreoffice", "libreoffice-writer"],
            check=True
        )
        print("✅ LibreOffice installé avec succès")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur d'installation : {e}")
        sys.exit(1)

def verify_libreoffice_installation():
    try:
        result = subprocess.run(
            ["libreoffice", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"Version installée : {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("LibreOffice non trouvé. Installation échouée.")
        return False



# def convert_docx_to_pdf(docx_path, output_dir="./data/uploads/pp"):
#     output_path = Path(output_dir) / f"{Path(docx_path).stem}.pdf"
#     try:
#         subprocess.run([
#             "libreoffice", "--headless", "--convert-to", "pdf",
#             "--outdir", str(output_dir),
#             str(docx_path)
#         ], check=True)
#         print(f"✅ Converti : {docx_path} -> {output_path}")
#         return output_path
#     except subprocess.CalledProcessError as e:
#         print(f"❌ Échec de conversion : {e}")
#         return None



# Configuration du logging



def convert_docx_to_pdf(docx_path, output_dir):
    """Conversion fiable avec unoconv"""
    try:
        docx_path = Path(docx_path)
        output_dir = Path(output_dir)
        pdf_path = output_dir / f"{docx_path.stem}.pdf"
                
        # Conversion
        subprocess.run([
            "unoconv",
            "-f", "pdf",
            "-o", str(pdf_path),
            str(docx_path)
        ], check=True, timeout=30)
        
        # Vérification du PDF généré
        if not pdf_path.exists():
            raise ValueError("Le fichier PDF n'a pas été créé")
        if pdf_path.stat().st_size < 1024:  # Vérifie la taille minimale
            raise ValueError("PDF trop petit (conversion probablement échouée)")
        
        return True
    except Exception as e:
        print(f"Échec de conversion : {e}")
        return False

def convert_with_unoserver(docx_path: str, output_dir: str, timeout: int = 120) -> str:
    """
    Version renforcée avec :
    - Timeout ajustable
    - Gestion propre du serveur
    - Nettoyage des ressources
    """
    docx_path = Path(docx_path)
    output_dir = Path(output_dir)
    pdf_path = output_dir / f"{docx_path.stem}.pdf"
    
    with tempfile.TemporaryDirectory() as tmp_profile:
        try:
            # 1. Démarrer le serveur
            server = subprocess.Popen(
                ["unoserver", "--port", "2002", "--user-profile", tmp_profile],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            time.sleep(3)  # Attente critique pour l'initialisation

            # 2. Exécuter la conversion avec timeout étendu
            subprocess.run(
                [
                    "unoconvert",
                    "--port", "2002",
                    "--timeout", str(timeout),
                    str(docx_path),
                    str(pdf_path)
                ],
                check=True,
                timeout=timeout,
                stderr=subprocess.PIPE
            )

            return str(pdf_path) if pdf_path.exists() else None

        except subprocess.TimeoutExpired:
            print(f"Timeout dépassé ({timeout}s) pour {docx_path.name}")
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"Erreur de conversion (code {e.returncode}): {e.stderr.decode()}")
            return None
            
        finally:
            # 3. Nettoyage garantie
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=5)