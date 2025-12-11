import psutil
import platform
import socket
import time
import os
import datetime
import jinja2
from pathlib import Path

# --- FONCTIONS UTILITAIRES ---

def obtenir_ip():
    """Tente de récupérer l'IP locale utilisée pour sortir vers internet"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # On ne se connecte pas vraiment, on regarde juste quelle interface serait utilisée
        s.connect(('8.8.8.8', 1)) 
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def secondes_en_temps(seconds):
    """Convertit des secondes en format lisible (H:M:S)"""
    return str(datetime.timedelta(seconds=int(seconds)))
def analyser_dossier():
    # Détection du dossier Documents
    if os.name == 'nt':
        dossier_cible = Path.home() / "Documents"
    else:
        dossier_cible = Path.home()

    print(f"Analyse en cours dans : {dossier_cible} ...")
    
    # Extensions ciblées
    cibles = {'.txt': 0, '.py': 0, '.pdf': 0, '.jpg': 0}
    
    try:
        # On scanne tout
        for fichier in dossier_cible.rglob('*'):
            if fichier.is_file():
                ext = fichier.suffix.lower()
                if ext in cibles:
                    cibles[ext] += 1
                    
    except PermissionError:
        pass

    # On calcule le total UNIQUEMENT des fichiers trouvés dans 'cibles'
    # sum(cibles.values()) additionne les 4 compteurs
    total_restreint = sum(cibles.values())

    return dossier_cible, cibles, total_restreint

def obtenir_top_processus():
    """Récupère la liste des processus et trie les top 3"""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            p_info = p.info
            # On ignore le processus PID 0 (System Idle Process)
            # ignore ceux qui ont 0% de CPU pour éviter le bruit
            if p_info['pid'] == 0 or p_info['cpu_percent'] == 0.0:
                continue
            # On stocke les infos dans une liste simple
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    # Tri pour le CPU (du plus grand au plus petit)
    top_cpu = sorted(procs, key=lambda p: p['cpu_percent'], reverse=True)[:3]
    
    # Tri pour la RAM
    top_ram = sorted(procs, key=lambda p: p['memory_percent'], reverse=True)[:3]
    
    return top_cpu, top_ram

# --- BOUCLE PRINCIPALE ---

def dashboard_expert():
    # 1. Infos statiques (qui ne changent pas chaque seconde)
    nom_machine = socket.gethostname()
    os_info = f"{platform.system()} {platform.release()}"
    ip_machine = obtenir_ip()
    
    boot_timestamp = psutil.boot_time()
    date_demarrage = datetime.datetime.fromtimestamp(boot_timestamp).strftime("%Y-%m-%d %H:%M:%S")
    path_scan, stats_fichiers, total_selection = analyser_dossier()

    # Initialisation CPU pour la première lecture
    psutil.cpu_percent(interval=None)

    print("Initialisation des données... (Patientez 1s)")
    time.sleep(1)

    try:
        while True:
            # --- CALCULS ---
            
            # Ressources globales
            cpu_pct = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            nb_users = len(psutil.users())
            coeurs_physiques = psutil.cpu_count(logical=False)
            coeurs_logique = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=0)
            freq = psutil.cpu_freq()
            freq_val = freq.current if freq else 0

            # Mémoire RAM
            ram_total = mem.total / (1024**3)
            ram_used = mem.used / (1024**3)
            
            # Uptime
            uptime_sec = time.time() - boot_timestamp
            uptime_str = secondes_en_temps(uptime_sec)

            # Top Processus
            top_cpu_list, top_ram_list = obtenir_top_processus()

            # --- AFFICHAGE ---
            os.system('cls' if os.name == 'nt' else 'clear')

            print(f"===== MONITEUR EXPERT =====")
            print(f"nom_machine: {nom_machine}")
            print(f"OS: {os_info} | IP: {ip_machine}")
            print(f"Boot: {date_demarrage} | Uptime: {uptime_str}")
            print(f"Utilisateurs connectés: {nb_users}")
            print("-" * 50)

            # Section processeur
            print(" [Processeur CPU]")
            print(f"Cœurs physiques/logique(threads) : {coeurs_physiques}/{coeurs_logique}")
            print(f"Utilisation : {cpu_percent}%")
            print(f"Fréquence   : {freq_val:.0f} Mhz")
            print("-" * 50)

            # Section Mémoire
            print(" [MÉMOIRE VIVE (RAM)]")
            print(f"utiliser    : {ram_used:.2f} GB ")
            print(f"total       : {ram_total:.2f} GB")
            print(f"Utilisation : {mem.percent}%")
            print("-" * 50)

            # Section Top Processus CPU
            print(" [TOP 3 - CONSOMMATION CPU]")
            print(f" {'PID':<6} {'NOM':<25} {'CPU %':<10}")
            for p in top_cpu_list:
                print(f" {p['pid']:<6} {p['name'][:24]:<25} {p['cpu_percent']}%")
            
            print("") 

            # Section Top Processus RAM
            print(" [TOP 3 - CONSOMMATION RAM]")
            print(f" {'PID':<6} {'NOM':<25} {'RAM %':<10}")
            for p in top_ram_list:
                # memory_percent retourne un chiffre précis, on l'arrondit
                print(f" {p['pid']:<6} {p['name'][:24]:<25} {p['memory_percent']:.2f}%")

            print("-" * 50)
             # section Statistiques Fichiers
            print(f" [STATISTIQUES FICHIERS] Dossier : {path_scan.name}")
            print(f" Total des fichiers ciblés trouvés : {total_selection}")
            
            print(f" {'TYPE':<6} | {'NOMBRE':<8} | {'% DU GROUPE':<12}")
            print(" " + "-" * 30)
            
            for ext, count in stats_fichiers.items():
                # Calcul : (Nombre Fichier / Total des 4 types) * 100
                if total_selection > 0:
                    pct = (count / total_selection) * 100
                else:
                    pct = 0.0

                print(f" {ext:<6} | {count:<8} | {pct:>5.1f}%")
            
            print("-" * 60)
            print(" CTRL+C pour arrêter")

            # --- GÉNÉRATION JINJA2 ---
            
            # Le dossier où Apache lit les fichiers
            dossier_html = "/var/www/html"
            
            # # Le fichier de sortie 
            fichier_sortie = os.path.join(dossier_html, 'index.html')
            
            # On dit à Jinja de chercher 'template.html' directement dans /var/www/html
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(dossier_html))
            try:
                template = env.get_template("template.html")
                
                # 2. On prépare toutes les données à envoyer au HTML
                contexte = {
                    'nom_machine': nom_machine,
                    'os_info': os_info,
                    'ip_machine': ip_machine,
                    'date_demarrage': date_demarrage,
                    'uptime': uptime_str,
                    'nb_users': nb_users,
                    
                    # CPU
                    'coeurs_physiques': coeurs_physiques,
                    'coeurs_logique': coeurs_logique,
                    'cpu_percent': cpu_percent,
                    'freq_val': freq_val,
                    
                    # RAM
                    'ram_used': ram_used,
                    'ram_total': ram_total,
                    'ram_percent': mem.percent,
                    
                    # PROCESSUS EN COURS 
                    'top_cpu': top_cpu_list,
                    'top_ram': top_ram_list,
                    
                    # FICHIERS
                    'dossier_scan': path_scan.name,
                    'total_fichiers': total_selection,
                    'stats_fichiers': stats_fichiers  # Dictionnaire {'txt': 0, 'py': 5...}
                }

                # 3. Rendu du HTML
                html_content = template.render(contexte)
                
                # 4. Écriture du fichier final
                with open(fichier_sortie, "w", encoding="utf-8") as fp:
                    fp.write(html_content)

            except PermissionError:
                print(f"ERREUR CRITIQUE : Permission refusée d'écrire dans {dossier_html}")        
            except Exception as e:
                print(f"Erreur lors de la génération HTML : {e}")

            # Pause avant rafraichissement
            time.sleep(30)

    except KeyboardInterrupt:
        print("\nArrêt du programme.")

if __name__ == "__main__":
    dashboard_expert()