from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import re
from flask_cors import CORS
from datetime import datetime
import os
import threading
import time
import schedule
import requests

app = Flask(__name__)
CORS(app)

# Configuration pour Render
PORT = int(os.environ.get('PORT', 10000))
BASE_URL = os.environ.get('BASE_URL', f'http://localhost:{PORT}')
CHECK_INTERVAL_MINUTES = int(os.environ.get('CHECK_INTERVAL_MINUTES', 14))

# Chemin de la base de données (persistant sur Render)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paiements.db')

def get_db_connection():
    """Établit une connexion à la base de données SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    try:
        with get_db_connection() as conn:
            # Table des paiements
            conn.execute('''
                CREATE TABLE IF NOT EXISTS paiements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trans_id TEXT UNIQUE,
                    montant REAL,
                    numero TEXT,
                    date_paiement DATETIME DEFAULT CURRENT_TIMESTAMP,
                    statut TEXT DEFAULT 'recu',
                    date_utilisation DATETIME NULL
                )
            ''')
            
            # Table pour les paiements automatiques configurés
            conn.execute('''
                CREATE TABLE IF NOT EXISTS paiements_auto (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT NOT NULL,
                    montant REAL NOT NULL,
                    service_nom TEXT,
                    actif BOOLEAN DEFAULT 1,
                    date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
                    dernier_check DATETIME,
                    UNIQUE(numero, montant, service_nom)
                )
            ''')
            
            # Table pour l'historique des auto-appels
            conn.execute('''
                CREATE TABLE IF NOT EXISTS autoappel_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_execution DATETIME DEFAULT CURRENT_TIMESTAMP,
                    paiements_verifies INTEGER DEFAULT 0,
                    paiements_utilises INTEGER DEFAULT 0,
                    erreurs TEXT,
                    statut TEXT
                )
            ''')
            conn.commit()
            print("✅ Base de données initialisée avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")

# Initialiser la base de données au démarrage
init_db()

def parser_sms_orange(message):
    """
    Parse un message Orange Money pour extraire:
    - Montant
    - Numéro de l'expéditeur (8 chiffres)
    - Transaction ID
    """
    try:
        # Pattern pour extraire les informations
        pattern = r"Vous avez recu (\d+\.?\d*) FCFA du (\d+),.*?Trans ID: ([A-Z0-9.]+)"
        match = re.search(pattern, message)
        
        if match:
            montant = float(match.group(1))
            numero = match.group(2)
            trans_id = match.group(3)
            
            return {
                'success': True,
                'montant': montant,
                'numero': numero,
                'trans_id': trans_id
            }
        else:
            return {'success': False, 'message': 'Format SMS non reconnu'}
            
    except Exception as e:
        return {'success': False, 'message': f'Erreur parsing: {str(e)}'}

def verifier_et_utiliser_paiements_auto():
    """
    Fonction qui vérifie et utilise automatiquement les paiements
    pour les numéros configurés dans paiements_auto
    """
    print(f"[{datetime.now()}] 🔍 Début de la vérification automatique des paiements...")
    
    stats = {
        'paiements_verifies': 0,
        'paiements_utilises': 0,
        'erreurs': []
    }
    
    try:
        with get_db_connection() as conn:
            # Récupérer tous les paiements automatiques actifs
            cur = conn.execute(
                'SELECT * FROM paiements_auto WHERE actif = 1'
            )
            paiements_auto = cur.fetchall()
            
            if not paiements_auto:
                print("ℹ️ Aucun paiement automatique configuré")
                return stats
            
            for paiement_auto in paiements_auto:
                numero = paiement_auto['numero']
                montant = paiement_auto['montant']
                service_nom = paiement_auto['service_nom'] or "Service Auto"
                
                print(f"🔎 Vérification pour {numero} - {montant}F ({service_nom})")
                stats['paiements_verifies'] += 1
                
                try:
                    # Appeler l'API de vérification
                    response = requests.post(
                        f"{BASE_URL}/api/verifier_paiement",
                        json={'numero': numero, 'montant': montant},
                        timeout=10
                    )
                    
                    result = response.json()
                    
                    if result.get('success') and result.get('paiement_trouve'):
                        statut = result.get('statut')
                        if statut == 'utilise':
                            stats['paiements_utilises'] += 1
                            print(f"✅ Paiement utilisé avec succès pour {numero}")
                        elif statut == 'deja_utilise':
                            print(f"⚠️ Paiement déjà utilisé pour {numero}")
                        else:
                            print(f"❌ Aucun paiement trouvé pour {numero}")
                    
                    # Mettre à jour la date du dernier check
                    conn.execute(
                        'UPDATE paiements_auto SET dernier_check = CURRENT_TIMESTAMP WHERE id = ?',
                        (paiement_auto['id'],)
                    )
                    
                except requests.exceptions.RequestException as e:
                    error_msg = f"Erreur réseau pour {numero}: {str(e)}"
                    print(f"❌ {error_msg}")
                    stats['erreurs'].append(error_msg)
                except Exception as e:
                    error_msg = f"Erreur pour {numero}: {str(e)}"
                    print(f"❌ {error_msg}")
                    stats['erreurs'].append(error_msg)
            
            # Enregistrer l'historique de l'exécution
            conn.execute('''
                INSERT INTO autoappel_history 
                (paiements_verifies, paiements_utilises, erreurs, statut) 
                VALUES (?, ?, ?, ?)
            ''', (
                stats['paiements_verifies'],
                stats['paiements_utilises'],
                '; '.join(stats['erreurs']) if stats['erreurs'] else None,
                'succes' if not stats['erreurs'] else 'erreur'
            ))
            conn.commit()
            
            print(f"✅ Vérification terminée: {stats['paiements_utilises']} paiements utilisés sur {stats['paiements_verifies']} vérifiés")
    
    except Exception as e:
        print(f"❌ Erreur générale dans la vérification automatique: {str(e)}")
        stats['erreurs'].append(f"Erreur générale: {str(e)}")
    
    return stats

def run_scheduler():
    """Exécute le planificateur toutes les X minutes"""
    print(f"⏰ Scheduler démarré. Vérification toutes les {CHECK_INTERVAL_MINUTES} minutes")
    
    # Planifier la tâche
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(verifier_et_utiliser_paiements_auto)
    
    # Exécuter une première fois au démarrage
    print("🚀 Première vérification immédiate...")
    verifier_et_utiliser_paiements_auto()
    
    # Boucle principale du scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes

# =============== ROUTES API ===============

@app.route('/health')
def health_check():
    """Endpoint de health check pour Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Orange Money Paiement API',
        'environment': 'production' if os.environ.get('RENDER') else 'development',
        'base_url': BASE_URL,
        'check_interval_minutes': CHECK_INTERVAL_MINUTES
    })

@app.route('/')
def home():
    """Page d'accueil"""
    return send_from_directory('.', 'paiement.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Servir les fichiers statiques"""
    return send_from_directory('.', filename)

# API pour recevoir les SMS de paiement
@app.route('/api/reception_paiement', methods=['POST'])
def reception_paiement():
    """Endpoint qui reçoit les SMS de paiement"""
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({'success': False, 'message': 'Message manquant'}), 400
    
    message = data['message']
    
    # Parser le message SMS
    resultat_parsing = parser_sms_orange(message)
    
    if not resultat_parsing['success']:
        return jsonify(resultat_parsing), 400
    
    # Extraire les données
    montant = resultat_parsing['montant']
    numero = resultat_parsing['numero']
    trans_id = resultat_parsing['trans_id']
    
    try:
        # Enregistrer dans la base de données
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO paiements (trans_id, montant, numero, statut) VALUES (?, ?, ?, "recu")',
                (trans_id, montant, numero)
            )
            conn.commit()
        
        # Vérifier si ce paiement correspond à un paiement automatique configuré
        with get_db_connection() as conn:
            cur = conn.execute(
                'SELECT * FROM paiements_auto WHERE numero = ? AND montant = ? AND actif = 1',
                (numero, montant)
            )
            if cur.fetchone():
                print(f"💰 Paiement reçu pour un service automatique: {numero} - {montant}F")
        
        return jsonify({
            'success': True,
            'message': 'Paiement enregistré avec succès',
            'data': {
                'trans_id': trans_id,
                'montant': montant,
                'numero': numero,
                'statut': 'recu',
                'date': datetime.now().isoformat()
            }
        })
        
    except sqlite3.IntegrityError:
        return jsonify({
            'success': False,
            'message': 'Cette transaction a déjà été enregistrée'
        }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur base de données: {str(e)}'
        }), 500

@app.route('/api/verifier_paiement', methods=['POST'])
def verifier_paiement():
    """Vérifie si un paiement existe et le marque comme utilisé"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    numero = data.get('numero')
    montant = data.get('montant')
    
    if not numero or not montant:
        return jsonify({
            'success': False, 
            'message': 'Numéro et montant requis'
        }), 400
    
    try:
        montant = float(montant)
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'message': 'Montant invalide'
        }), 400
    
    # Vérifier dans la base de données
    with get_db_connection() as conn:
        # Chercher un paiement correspondant non utilisé
        cur = conn.execute(
            'SELECT * FROM paiements WHERE numero = ? AND montant = ? AND statut = "recu" ORDER BY date_paiement DESC LIMIT 1',
            (numero, montant)
        )
        paiement = cur.fetchone()
        
        if paiement:
            # Marquer le paiement comme utilisé
            conn.execute(
                'UPDATE paiements SET statut = "utilise", date_utilisation = CURRENT_TIMESTAMP WHERE id = ?',
                (paiement['id'],)
            )
            conn.commit()
            
            return jsonify({
                'success': True,
                'paiement_trouve': True,
                'statut': 'utilise',
                'message': 'Paiement vérifié et marqué comme utilisé avec succès',
                'data': {
                    'trans_id': paiement['trans_id'],
                    'montant': paiement['montant'],
                    'numero': paiement['numero'],
                    'date_paiement': paiement['date_paiement'],
                    'date_utilisation': datetime.now().isoformat()
                }
            })
        else:
            # Vérifier si un paiement existe mais est déjà utilisé
            cur = conn.execute(
                'SELECT * FROM paiements WHERE numero = ? AND montant = ? AND statut = "utilise" ORDER BY date_paiement DESC LIMIT 1',
                (numero, montant)
            )
            paiement_utilise = cur.fetchone()
            
            if paiement_utilise:
                return jsonify({
                    'success': False,
                    'paiement_trouve': True,
                    'statut': 'deja_utilise',
                    'message': 'Ce paiement a déjà été utilisé',
                    'data': {
                        'trans_id': paiement_utilise['trans_id'],
                        'montant': paiement_utilise['montant'],
                        'numero': paiement_utilise['numero'],
                        'date_paiement': paiement_utilise['date_paiement'],
                        'date_utilisation': paiement_utilise['date_utilisation']
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'paiement_trouve': False,
                    'statut': 'non_trouve',
                    'message': 'Aucun paiement trouvé pour ce numéro et montant'
                })

# API pour gérer les paiements automatiques
@app.route('/api/paiements_auto/ajouter', methods=['POST'])
def ajouter_paiement_auto():
    """Ajouter un paiement à vérifier automatiquement"""
    data = request.get_json()
    
    if not data or 'numero' not in data or 'montant' not in data:
        return jsonify({'success': False, 'message': 'Numéro et montant requis'}), 400
    
    numero = data['numero']
    montant = data['montant']
    service_nom = data.get('service_nom', 'Service Auto')
    
    try:
        montant = float(montant)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Montant invalide'}), 400
    
    try:
        with get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO paiements_auto (numero, montant, service_nom, actif, dernier_check)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            ''', (numero, montant, service_nom))
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Paiement automatique configuré',
            'data': {
                'numero': numero,
                'montant': montant,
                'service_nom': service_nom,
                'actif': True
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur configuration: {str(e)}'
        }), 500

@app.route('/api/paiements_auto/liste', methods=['GET'])
def liste_paiements_auto():
    """Lister tous les paiements automatiques configurés"""
    with get_db_connection() as conn:
        cur = conn.execute('SELECT * FROM paiements_auto ORDER BY date_creation DESC')
        paiements = cur.fetchall()
        
        resultat = []
        for p in paiements:
            resultat.append(dict(p))
        
        return jsonify({
            'success': True,
            'paiements_auto': resultat,
            'total': len(resultat)
        })

@app.route('/api/paiements_auto/<int:id>/toggle', methods=['POST'])
def toggle_paiement_auto(id):
    """Activer/désactiver un paiement automatique"""
    data = request.get_json()
    actif = data.get('actif') if data else None
    
    if actif not in [True, False]:
        return jsonify({'success': False, 'message': 'Statut actif requis (true/false)'}), 400
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                'UPDATE paiements_auto SET actif = ? WHERE id = ?',
                (1 if actif else 0, id)
            )
            conn.commit()
            
            cur = conn.execute('SELECT * FROM paiements_auto WHERE id = ?', (id,))
            paiement = cur.fetchone()
            
            if not paiement:
                return jsonify({'success': False, 'message': 'Paiement non trouvé'}), 404
            
            return jsonify({
                'success': True,
                'message': f'Paiement automatique {"activé" if actif else "désactivé"}',
                'data': dict(paiement)
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur mise à jour: {str(e)}'
        }), 500

@app.route('/api/paiements_auto/<int:id>/supprimer', methods=['DELETE'])
def supprimer_paiement_auto(id):
    """Supprimer un paiement automatique"""
    try:
        with get_db_connection() as conn:
            conn.execute('DELETE FROM paiements_auto WHERE id = ?', (id,))
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Paiement automatique supprimé'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur suppression: {str(e)}'
        }), 500

@app.route('/api/autoappel/historique', methods=['GET'])
def historique_autoappel():
    """Voir l'historique des auto-appels"""
    limit = request.args.get('limit', 50, type=int)
    
    with get_db_connection() as conn:
        cur = conn.execute('''
            SELECT * FROM autoappel_history 
            ORDER BY date_execution DESC 
            LIMIT ?
        ''', (limit,))
        
        historique = []
        for row in cur.fetchall():
            historique.append(dict(row))
        
        # Statistiques des dernières 24h
        cur = conn.execute('''
            SELECT 
                COUNT(*) as total_executions,
                SUM(paiements_verifies) as total_verifies,
                SUM(paiements_utilises) as total_utilises,
                AVG(CASE WHEN statut = 'succes' THEN 1 ELSE 0 END) * 100 as taux_succes
            FROM autoappel_history 
            WHERE date_execution > datetime('now', '-1 day')
        ''')
        stats_24h = dict(cur.fetchone() or {})
        
        return jsonify({
            'success': True,
            'historique': historique,
            'statistiques_24h': stats_24h
        })

@app.route('/api/autoappel/forcer', methods=['POST'])
def forcer_autoappel():
    """Forcer une exécution immédiate de l'auto-appel"""
    print("🚀 Exécution forcée de l'auto-appel demandée...")
    
    try:
        stats = verifier_et_utiliser_paiements_auto()
        
        return jsonify({
            'success': True,
            'message': 'Auto-appel exécuté avec succès',
            'statistiques': stats,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de l\'auto-appel: {str(e)}'
        }), 500

@app.route('/api/historique_paiements', methods=['POST'])
def historique_paiements():
    """Retourne tous les paiements d'un numéro donné avec leur statut"""
    data = request.get_json()
    numero = data.get('numero') if data else None
    
    if not numero:
        return jsonify({'success': False, 'message': 'Numéro requis'}), 400
    
    with get_db_connection() as conn:
        cur = conn.execute(
            'SELECT * FROM paiements WHERE numero = ? ORDER BY date_paiement DESC',
            (numero,)
        )
        paiements = cur.fetchall()
        
        resultat = []
        for paiement in paiements:
            resultat.append({
                'trans_id': paiement['trans_id'],
                'montant': paiement['montant'],
                'numero': paiement['numero'],
                'date_paiement': paiement['date_paiement'],
                'statut': paiement['statut'],
                'date_utilisation': paiement['date_utilisation']
            })
        
        # Statistiques
        paiements_recu = [p for p in resultat if p['statut'] == 'recu']
        paiements_utilise = [p for p in resultat if p['statut'] == 'utilise']
        
        return jsonify({
            'success': True,
            'numero': numero,
            'total_paiements': len(resultat),
            'statistiques': {
                'paiements_recu': len(paiements_recu),
                'paiements_utilise': len(paiements_utilise),
                'montant_total': sum(p['montant'] for p in resultat),
                'montant_disponible': sum(p['montant'] for p in paiements_recu)
            },
            'paiements': resultat
        })

@app.route('/api/paiements_disponibles', methods=['POST'])
def paiements_disponibles():
    """Retourne seulement les paiements disponibles (non utilisés) d'un numéro"""
    data = request.get_json()
    numero = data.get('numero') if data else None
    
    if not numero:
        return jsonify({'success': False, 'message': 'Numéro requis'}), 400
    
    with get_db_connection() as conn:
        cur = conn.execute(
            'SELECT * FROM paiements WHERE numero = ? AND statut = "recu" ORDER BY date_paiement DESC',
            (numero,)
        )
        paiements = cur.fetchall()
        
        resultat = []
        for paiement in paiements:
            resultat.append({
                'trans_id': paiement['trans_id'],
                'montant': paiement['montant'],
                'numero': paiement['numero'],
                'date_paiement': paiement['date_paiement']
            })
        
        return jsonify({
            'success': True,
            'numero': numero,
            'paiements_disponibles': len(resultat),
            'montant_total_disponible': sum(p['montant'] for p in resultat),
            'paiements': resultat
        })

@app.route('/api/statistiques', methods=['GET'])
def statistiques():
    """Retourne des statistiques sur les paiements"""
    with get_db_connection() as conn:
        # Total des paiements
        cur = conn.execute('SELECT COUNT(*) as total FROM paiements')
        total_paiements = cur.fetchone()['total']
        
        # Paiements utilisés
        cur = conn.execute('SELECT COUNT(*) as utilises FROM paiements WHERE statut = "utilise"')
        paiements_utilises = cur.fetchone()['utilises']
        
        # Paiements disponibles
        cur = conn.execute('SELECT COUNT(*) as disponibles FROM paiements WHERE statut = "recu"')
        paiements_disponibles = cur.fetchone()['disponibles']
        
        # Montants
        cur = conn.execute('SELECT SUM(montant) as total_montant FROM paiements')
        total_montant = cur.fetchone()['total_montant'] or 0
        
        cur = conn.execute('SELECT SUM(montant) as montant_utilise FROM paiements WHERE statut = "utilise"')
        montant_utilise = cur.fetchone()['montant_utilise'] or 0
        
        cur = conn.execute('SELECT SUM(montant) as montant_disponible FROM paiements WHERE statut = "recu"')
        montant_disponible = cur.fetchone()['montant_disponible'] or 0
        
        # Paiements automatiques
        cur = conn.execute('SELECT COUNT(*) as total_auto FROM paiements_auto WHERE actif = 1')
        paiements_auto_actifs = cur.fetchone()['total_auto'] or 0
        
        # Derniers paiements
        cur = conn.execute('''
            SELECT * FROM paiements 
            ORDER BY date_paiement DESC 
            LIMIT 10
        ''')
        derniers_paiements = []
        for row in cur.fetchall():
            derniers_paiements.append(dict(row))
        
        # Dernier auto-appel
        cur = conn.execute('''
            SELECT * FROM autoappel_history 
            ORDER BY date_execution DESC 
            LIMIT 1
        ''')
        dernier_autoappel = dict(cur.fetchone() or {})
        
        return jsonify({
            'success': True,
            'statistiques': {
                'total_paiements': total_paiements,
                'paiements_utilises': paiements_utilises,
                'paiements_disponibles': paiements_disponibles,
                'total_montant': total_montant,
                'montant_utilise': montant_utilise,
                'montant_disponible': montant_disponible,
                'paiements_auto_actifs': paiements_auto_actifs,
                'intervalle_verification_minutes': CHECK_INTERVAL_MINUTES
            },
            'derniers_paiements': derniers_paiements,
            'dernier_autoappel': dernier_autoappel
        })

# Démarrage du scheduler dans un thread séparé
def start_scheduler():
    """Démarre le scheduler dans un thread séparé"""
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print(f"⏰ Auto-appel programmé toutes les {CHECK_INTERVAL_MINUTES} minutes")

def main():
    """Point d'entrée principal de l'application"""
    # Démarrer le scheduler
    start_scheduler()
    
    # Afficher les informations de configuration
    print("=" * 60)
    print("🚀 Serveur Orange Money Paiement")
    print("=" * 60)
    print(f"Environnement: {'Production (Render)' if os.environ.get('RENDER') else 'Développement'}")
    print(f"Port: {PORT}")
    print(f"Base URL: {BASE_URL}")
    print(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    print(f"Database path: {DB_PATH}")
    print("=" * 60)
    print("📊 Endpoints disponibles:")
    print(f"  • Page principale: {BASE_URL}/")
    print(f"  • Health check: {BASE_URL}/health")
    print(f"  • API Statistiques: {BASE_URL}/api/statistiques")
    print(f"  • Réception paiement: {BASE_URL}/api/reception_paiement")
    print("=" * 60)
    
    # Démarrer le serveur avec Waitress
    from waitress import serve
    serve(
        app, 
        host='0.0.0.0', 
        port=PORT, 
        threads=4,
        ident='OrangeMoneyAPI'
    )

if __name__ == '__main__':
    main()