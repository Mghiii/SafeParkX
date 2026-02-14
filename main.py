from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, send_file
from flask_socketio import SocketIO as FlaskSocketIO, emit
import mysql.connector
import os
import cv2
from datetime import datetime, timedelta
import threading
import time
import random
import string
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = FlaskSocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configuration de la caméra
camera = None
camera_lock = threading.Lock()
capture_folder = 'static/captures'
if not os.path.exists(capture_folder):
    os.makedirs(capture_folder)

# Thread pour les mises à jour en temps réel (désactivé temporairement)
update_thread = None
stop_updates = True  # Désactivé pour éviter les erreurs

def generate_unique_matricule():
    """Génère un matricule unique au format XX-123-XX"""
    max_attempts = 100
    attempts = 0
    
    while attempts < max_attempts:
        try:
            # Format: XX-123-XX (2 lettres, 3 chiffres, 2 lettres)
            letters1 = ''.join(random.choices(string.ascii_uppercase, k=2))
            numbers = ''.join(random.choices(string.digits, k=3))
            letters2 = ''.join(random.choices(string.ascii_uppercase, k=2))
            matricule = f"{letters1}-{numbers}-{letters2}"
            
            # Vérifier si le matricule existe déjà
            cursor.execute("SELECT COUNT(*) as count FROM vehicule WHERE matricule = %s", (matricule,))
            result = cursor.fetchone()
            if result and result['count'] == 0:
                return matricule
            attempts += 1
        except Exception as e:
            print(f"Erreur lors de la génération du matricule: {e}")
            attempts += 1
            # Attendre un peu avant de réessayer
            time.sleep(0.1)
    
    # Si on n'arrive pas à générer un matricule unique, retourner un matricule avec timestamp
    timestamp = datetime.now().strftime("%H%M%S")
    return f"XX-{timestamp}-XX"

def reset_database_connection():
    """Réinitialise la connexion à la base de données"""
    global db, cursor
    try:
        if db and db.is_connected():
            db.close()
    except:
        pass
    
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="SafeParkX"
        )
        cursor = db.cursor(dictionary=True)
        return True
    except Exception as e:
        print(f"Erreur de reconnexion à la base de données: {e}")
        return False



def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)  # Utilise la caméra par défaut
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return camera

def release_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None

def generate_frames():
    """Génère les frames de la caméra pour le streaming"""
    camera = get_camera()
    while True:
        with camera_lock:
            success, frame = camera.read()
            if not success:
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)  # Délai pour réduire la charge CPU

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="SafeParkX"
)
cursor = db.cursor(dictionary=True)

# Login page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT * FROM admin WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        if user:
            session['admin'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('components/index.html')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    # Récupérer les statistiques du parking
    cursor.execute("SELECT COUNT(*) as total FROM places")
    total_places = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as occupees FROM places WHERE etat = 1")
    places_occupees = cursor.fetchone()['occupees']
    
    cursor.execute("SELECT COUNT(*) as libres FROM places WHERE etat = 0")
    places_libres = cursor.fetchone()['libres']
    
    cursor.execute("SELECT COUNT(*) as vehicules FROM vehicule WHERE date_sortie IS NULL")
    vehicules_presents = cursor.fetchone()['vehicules']
    
    cursor.execute("SELECT type_vehicule, COUNT(*) as count FROM vehicule WHERE date_sortie IS NULL GROUP BY type_vehicule")
    types_vehicules = cursor.fetchall()
    
    cursor.execute("SELECT DATE(date_entrer) as date, COUNT(*) as count FROM vehicule WHERE date_entrer >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY DATE(date_entrer) ORDER BY date")
    entrees_semaine = cursor.fetchall()
    
    stats = {
        'total_places': total_places,
        'places_occupees': places_occupees,
        'places_libres': places_libres,
        'vehicules_presents': vehicules_presents,
        'taux_occupation': round((places_occupees / total_places * 100) if total_places > 0 else 0, 1),
        'types_vehicules': types_vehicules,
        'entrees_semaine': entrees_semaine
    }
    
    return render_template('components/dashboard.html', stats=stats)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/parking')
def parking():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    # Récupérer les véhicules actuellement au parking
    try:
        cursor.execute("""
            SELECT 
                v.id_vehicule,
                v.id_admin,
                v.matricule,
                v.type_vehicule,
                v.date_entrer,
                v.id_place,
                v.image_path,
                v.id_ticket,
                t.id_ticket as ticket_id
            FROM vehicule v 
            LEFT JOIN ticket t ON v.id_ticket = t.id_ticket
            WHERE v.date_sortie IS NULL
            ORDER BY v.id_place
        """)
    except Exception as e:
        # Si la colonne image_path n'existe pas, utiliser une requête sans elle
        cursor.execute("""
            SELECT 
                v.id_vehicule,
                v.id_admin,
                v.matricule,
                v.type_vehicule,
                v.date_entrer,
                v.id_place,
                NULL as image_path,
                v.id_ticket,
                t.id_ticket as ticket_id
            FROM vehicule v 
            LEFT JOIN ticket t ON v.id_ticket = t.id_ticket
            WHERE v.date_sortie IS NULL
            ORDER BY v.id_place
        """)
    vehicules = cursor.fetchall()
    
    # Statistiques du parking
    cursor.execute("SELECT COUNT(*) as total FROM places")
    total_places = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as vehicules FROM vehicule WHERE date_sortie IS NULL")
    vehicules_presents = cursor.fetchone()['vehicules']
    
    places_libres = total_places - vehicules_presents
    taux_occupation = round((vehicules_presents / total_places * 100) if total_places > 0 else 0, 1)
    
    stats = {
        'vehicules_presents': vehicules_presents,
        'places_libres': places_libres,
        'taux_occupation': taux_occupation
    }
    
    return render_template('components/parking.html', stats=stats, vehicules=vehicules)

@app.route('/log')
def log():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    # Récupérer les véhicules sortis depuis la table log_vehicules
    try:
        cursor.execute("""
            SELECT 
                lv.id_vehicule_original as id_vehicule,
                lv.matricule,
                lv.type_vehicule,
                lv.date_entrer,
                lv.date_sortie,
                lv.duree_jours,
                lv.duree_heures,
                lv.duree_minutes,
                lv.duree_secondes,
                lv.montant_total,
                lv.id_place,
                lv.id_admin,
                lv.image_path
            FROM log_vehicules lv 
            ORDER BY lv.date_sortie DESC
        """)
        vehicules_sortis = cursor.fetchall()
    except:
        # Si la table log_vehicules n'existe pas encore
        vehicules_sortis = []
    
    # Récupérer les véhicules actuels
    cursor.execute("""
        SELECT 
            v.id_vehicule,
            v.matricule,
            v.type_vehicule,
            v.date_entrer,
            v.id_place,
            v.id_admin,
            v.image_path
        FROM vehicule v 
        ORDER BY v.date_entrer DESC
    """)
    vehicules_actuels = cursor.fetchall()
    
    # Statistiques
    total_vehicules = len(vehicules_actuels) + len(vehicules_sortis)
    vehicules_sortis_count = len(vehicules_sortis)
    
    # Entrées des 30 derniers jours (combiner actuels et sortis)
    cursor.execute("""
        SELECT DATE(date_entrer) as date, COUNT(*) as count 
        FROM (
            SELECT date_entrer FROM vehicule 
            UNION ALL 
            SELECT date_entrer FROM log_vehicules
        ) all_entries
        WHERE date_entrer >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) 
        GROUP BY DATE(date_entrer) 
        ORDER BY date
    """)
    entrees_historique = cursor.fetchall()
    
    stats = {
        'total_vehicules': total_vehicules,
        'vehicules_actuels': len(vehicules_actuels),
        'vehicules_sortis': vehicules_sortis_count,
        'entrees_historique': entrees_historique
    }
    
    return render_template('components/log.html', 
                         stats=stats, 
                         vehicules_actuels=vehicules_actuels,
                         vehicules_sortis=vehicules_sortis)

@app.route('/settings')
def settings():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    # Récupérer les paramètres actuels (créer des valeurs par défaut si pas de table)
    try:
        cursor.execute("SELECT * FROM settings LIMIT 1")
        settings_data = cursor.fetchone()
        if not settings_data:
            # Créer la table settings si elle n'existe pas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    parking_name VARCHAR(100) DEFAULT 'SafeParkX',
                    total_places INT DEFAULT 20,
                    price_per_hour DECIMAL(5,2) DEFAULT 2.50,
                    session_timeout INT DEFAULT 30,
                    maintenance_mode BOOLEAN DEFAULT FALSE,
                    email_notifications BOOLEAN DEFAULT TRUE
                )
            """)
            cursor.execute("INSERT INTO settings () VALUES ()")
            db.commit()
            cursor.execute("SELECT * FROM settings LIMIT 1")
            settings_data = cursor.fetchone()
    except:
        settings_data = {
            'parking_name': 'SafeParkX',
            'total_places': 20,
            'price_per_hour': 2.50,
            'session_timeout': 30,
            'maintenance_mode': False,
            'email_notifications': True
        }
    
    # Récupérer la liste des admins
    cursor.execute("SELECT * FROM admin ORDER BY id")
    admins = cursor.fetchall()
    
    # Récupérer l'admin actuel
    cursor.execute("SELECT * FROM admin WHERE email = %s", (session['admin'],))
    current_admin = cursor.fetchone()
    
    return render_template('components/settings.html', 
                         settings=settings_data, 
                         admins=admins, 
                         current_admin=current_admin)

@app.route('/settings/general', methods=['POST'])
def settings_general():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    try:
        parking_name = request.form['parking_name']
        total_places = int(request.form['total_places'])
        price_per_hour = float(request.form['price_per_hour'])
        
        cursor.execute("""
            UPDATE settings SET 
            parking_name = %s, 
            total_places = %s, 
            price_per_hour = %s 
            WHERE id = 1
        """, (parking_name, total_places, price_per_hour))
        db.commit()
        
        flash('Paramètres généraux mis à jour avec succès !', 'success')
    except Exception as e:
        flash('Erreur lors de la mise à jour des paramètres', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/settings/system', methods=['POST'])
def settings_system():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    try:
        session_timeout = int(request.form['session_timeout'])
        maintenance_mode = request.form['maintenance_mode'] == '1'
        email_notifications = request.form['email_notifications'] == '1'
        
        cursor.execute("""
            UPDATE settings SET 
            session_timeout = %s, 
            maintenance_mode = %s, 
            email_notifications = %s 
            WHERE id = 1
        """, (session_timeout, maintenance_mode, email_notifications))
        db.commit()
        
        flash('Configuration système mise à jour avec succès !', 'success')
    except Exception as e:
        flash('Erreur lors de la mise à jour de la configuration', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/settings/password', methods=['POST'])
def settings_password():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    # Vérifier le mot de passe actuel
    cursor.execute("SELECT * FROM admin WHERE email = %s AND password = %s", 
                  (session['admin'], current_password))
    admin = cursor.fetchone()
    
    if not admin:
        flash('Mot de passe actuel incorrect', 'danger')
        return redirect(url_for('settings'))
    
    if new_password != confirm_password:
        flash('Les nouveaux mots de passe ne correspondent pas', 'danger')
        return redirect(url_for('settings'))
    
    if len(new_password) < 6:
        flash('Le nouveau mot de passe doit contenir au moins 6 caractères', 'danger')
        return redirect(url_for('settings'))
    
    try:
        cursor.execute("UPDATE admin SET password = %s WHERE email = %s", 
                      (new_password, session['admin']))
        db.commit()
        flash('Mot de passe modifié avec succès !', 'success')
    except Exception as e:
        flash('Erreur lors du changement de mot de passe', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/settings/add-admin', methods=['POST'])
def settings_add_admin():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    nom = request.form['nom']
    prenom = request.form['prenom']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    
    if password != confirm_password:
        flash('Les mots de passe ne correspondent pas', 'danger')
        return redirect(url_for('settings'))
    
    if len(password) < 6:
        flash('Le mot de passe doit contenir au moins 6 caractères', 'danger')
        return redirect(url_for('settings'))
    
    # Vérifier si l'email existe déjà
    cursor.execute("SELECT * FROM admin WHERE email = %s", (email,))
    if cursor.fetchone():
        flash('Cet email est déjà utilisé', 'danger')
        return redirect(url_for('settings'))
    
    try:
        cursor.execute("INSERT INTO admin (nom, prenom, email, password) VALUES (%s, %s, %s, %s)", 
                      (nom, prenom, email, password))
        db.commit()
        flash('Administrateur ajouté avec succès !', 'success')
    except Exception as e:
        flash('Erreur lors de l\'ajout de l\'administrateur', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/settings/delete-admin/<int:admin_id>', methods=['DELETE'])
def settings_delete_admin(admin_id):
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'})
    
    # Empêcher la suppression de soi-même
    cursor.execute("SELECT * FROM admin WHERE email = %s", (session['admin'],))
    current_admin = cursor.fetchone()
    
    if current_admin['id'] == admin_id:
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous supprimer vous-même'})
    
    try:
        cursor.execute("DELETE FROM admin WHERE id = %s", (admin_id,))
        db.commit()
        return jsonify({'success': True, 'message': 'Administrateur supprimé avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erreur lors de la suppression'})

@app.route('/vehicule/<int:vehicule_id>')
def vehicule_details(vehicule_id):
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    try:
        # D'abord chercher dans les véhicules actuels
        cursor.execute("""
            SELECT 
                v.*,
                p.etat as place_etat,
                v.image_path
            FROM vehicule v 
            LEFT JOIN places p ON v.id_place = p.id_place
            WHERE v.id_vehicule = %s
        """, (vehicule_id,))
        vehicule = cursor.fetchone()
        
        if vehicule:
            # Véhicule actuel
            return render_template('components/vehicule_details.html', vehicule=vehicule)
        
        # Si pas trouvé, chercher dans les logs
        cursor.execute("""
            SELECT 
                lv.*,
                'SORTI' as place_etat
            FROM log_vehicules lv 
            WHERE lv.id_vehicule_original = %s
        """, (vehicule_id,))
        vehicule = cursor.fetchone()
        
        if vehicule:
            # Véhicule sorti
            return render_template('components/vehicule_details.html', vehicule=vehicule, is_exited=True)
        
        return "Véhicule non trouvé", 404
        
    except Exception as e:
        return f"Erreur: {str(e)}", 500

@app.route('/camera')
def camera_page():
    if 'admin' not in session:
        return redirect(url_for('index'))
    
    # Récupérer la liste des captures existantes
    captures = []
    if os.path.exists(capture_folder):
        for filename in os.listdir(capture_folder):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(capture_folder, filename)
                file_stat = os.stat(file_path)
                captures.append({
                    'filename': filename,
                    'path': f'/static/captures/{filename}',
                    'size': file_stat.st_size,
                    'date': datetime.fromtimestamp(file_stat.st_mtime)
                })
    
    # Trier par date (plus récent en premier)
    captures.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('components/camera.html', captures=captures)

@app.route('/video_feed')
def video_feed():
    """Route pour le streaming vidéo de la caméra"""
    if 'admin' not in session:
        return "Non autorisé", 403
    
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture_image():
    """Route pour capturer une image depuis la caméra et créer un véhicule"""
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'})
    
    try:
        # Type de véhicule par défaut
        type_vehicule = 'Véhicule'
        
        camera = get_camera()
        with camera_lock:
            success, frame = camera.read()
            if success:
                # Générer un nom de fichier unique avec timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"
                filepath = os.path.join(capture_folder, filename)
                
                # Sauvegarder l'image
                cv2.imwrite(filepath, frame)
                
                # Générer un matricule unique
                matricule = generate_unique_matricule()
                
                # Récupérer l'ID de l'admin connecté
                try:
                    cursor.execute("SELECT id FROM admin WHERE email = %s", (session['admin'],))
                    admin_result = cursor.fetchone()
                    if admin_result:
                        admin_id = admin_result['id']
                    else:
                        return jsonify({'success': False, 'message': 'Admin non trouvé'})
                except Exception as e:
                    # Essayer de reconnecter à la base de données
                    if reset_database_connection():
                        cursor.execute("SELECT id FROM admin WHERE email = %s", (session['admin'],))
                        admin_result = cursor.fetchone()
                        if admin_result:
                            admin_id = admin_result['id']
                        else:
                            return jsonify({'success': False, 'message': 'Admin non trouvé'})
                    else:
                        return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'})
                
                # Vérifier si la colonne image_path existe, sinon la créer
                try:
                    cursor.execute("DESCRIBE vehicule")
                    columns = [column[0] for column in cursor.fetchall()]
                    if 'image_path' not in columns:
                        cursor.execute("ALTER TABLE vehicule ADD COLUMN image_path VARCHAR(255) DEFAULT NULL AFTER id_place")
                        db.commit()
                except Exception as e:
                    print(f"Erreur lors de la vérification/création de la colonne: {e}")
                
                # Créer un nouveau véhicule avec l'image
                try:
                    # Trouver une place libre
                    cursor.execute("SELECT id_place FROM places WHERE etat = 0 LIMIT 1")
                    place_result = cursor.fetchone()
                    
                    if place_result:
                        place_id = place_result['id_place']
                        
                        # Créer le véhicule avec la place assignée
                        cursor.execute("""
                            INSERT INTO vehicule (matricule, type_vehicule, date_entrer, id_admin, image_path, id_place)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (matricule, type_vehicule, datetime.now().date(), admin_id, f'/static/captures/{filename}', place_id))
                        
                        # Récupérer l'ID du véhicule créé
                        vehicule_id = cursor.lastrowid
                        
                        # Créer un ticket pour ce véhicule
                        cursor.execute("""
                            INSERT INTO ticket (id_place, id_vehicule)
                            VALUES (%s, %s)
                        """, (place_id, vehicule_id))
                        
                        # Récupérer l'ID du ticket créé
                        ticket_id = cursor.lastrowid
                        
                        # Mettre à jour le véhicule avec l'ID du ticket
                        cursor.execute("""
                            UPDATE vehicule SET id_ticket = %s WHERE id_vehicule = %s
                        """, (ticket_id, vehicule_id))
                        
                        # Mettre à jour la place (la rendre occupée)
                        cursor.execute("""
                            UPDATE places 
                            SET etat = 1, id_vehicule = %s, id_admin = %s, id_ticket = %s
                            WHERE id_place = %s
                        """, (vehicule_id, admin_id, ticket_id, place_id))
                        
                    else:
                        # Pas de place libre, créer le véhicule sans place
                        cursor.execute("""
                            INSERT INTO vehicule (matricule, type_vehicule, date_entrer, id_admin)
                            VALUES (%s, %s, %s, %s)
                        """, (matricule, type_vehicule, datetime.now().date(), admin_id))
                        
                        # Récupérer l'ID du véhicule créé
                        vehicule_id = cursor.lastrowid
                    
                    db.commit()
                    
                    # Notification de succès
                    print(f"Véhicule {matricule} ajouté avec succès")
                    
                except Exception as e:
                    # Si l'insertion avec image_path échoue, essayer sans
                    cursor.execute("""
                        INSERT INTO vehicule (matricule, type_vehicule, date_entrer, id_admin)
                        VALUES (%s, %s, %s, %s)
                    """, (matricule, type_vehicule, datetime.now().date(), admin_id))
                    db.commit()
                    
                    # Notification de succès
                    print(f"Véhicule {matricule} ajouté avec succès")
                
                # Initialiser les variables pour le ticket
                ticket_id = None
                place_id = None
                
                # Générer le fichier ticket texte
                ticket_content = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        TICKET DE PARKING                                      ║
║                    SafeParkX - Système Automatique                            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  🎫 NUMÉRO DE TICKET: {ticket_id if ticket_id else 'N/A'}                     ║
║  🚗 MATRICULE: {matricule}                                                    ║
║  🚙 TYPE DE VÉHICULE: {type_vehicule}                                         ║
║  🅿️  PLACE ASSIGNÉE: {place_id if place_id else 'N/A'}                        ║
║  📅 DATE D'ENTRÉE: {datetime.now().strftime('%d/%m/%Y')}                      ║
║  🕐 HEURE D'ENTRÉE: {datetime.now().strftime('%H:%M:%S')}                     ║
║  👤 ADMIN: {admin_id:03d}                                                     ║
║                                                                               ║
║  ⚠️  IMPORTANT:                                                               ║
║  • Conservez ce ticket précieusement                                          ║
║  • Présentez-le à la sortie du parking                                        ║
║  • Le paiement se fait à la sortie                                            ║
║                                                                               ║
║  📞 CONTACT: deweb TECHNOLOGY                                                 ║
║  🌐 WWW.SAFEPARKX.COM | www.deweb.ma                                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                """
                
                # Créer le dossier tickets s'il n'existe pas
                tickets_folder = 'static/tickets'
                if not os.path.exists(tickets_folder):
                    os.makedirs(tickets_folder)
                
                # Générer le nom du fichier ticket
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ticket_filename = f'ticket_{matricule}_{timestamp}.txt'
                ticket_filepath = os.path.join(tickets_folder, ticket_filename)
                
                # Écrire le contenu du ticket
                with open(ticket_filepath, 'w', encoding='utf-8') as f:
                    f.write(ticket_content)
                
                return jsonify({
                    'success': True,
                    'message': f'Véhicule {matricule} ajouté avec succès !',
                    'filename': filename,
                    'path': f'/static/captures/{filename}',
                    'matricule': matricule,
                    'type_vehicule': type_vehicule,
                    'ticket_url': f'/static/tickets/{ticket_filename}',
                    'ticket_filename': ticket_filename
                })
            else:
                return jsonify({'success': False, 'message': 'Impossible de capturer l\'image'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/register_exit/<int:vehicule_id>', methods=['POST'])
def register_exit(vehicule_id):
    """Route pour enregistrer la sortie d'un véhicule"""
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'})
    
    try:
        # Vérifier si le véhicule existe
        cursor.execute("""
            SELECT * FROM vehicule WHERE id_vehicule = %s
        """, (vehicule_id,))
        vehicule = cursor.fetchone()
        
        if not vehicule:
            return jsonify({'success': False, 'message': 'Véhicule non trouvé'})
        
        # Calculer la durée et le montant
        date_entree = vehicule['date_entrer']
        if not date_entree:
            return jsonify({'success': False, 'message': 'Date d\'entrée manquante pour ce véhicule'})
        
        date_sortie = datetime.now().date()
        duree_totale = date_sortie - date_entree
        jours = duree_totale.days
        total_minutes = jours * 24 * 60
        montant = total_minutes * 0.5  # 0.5€ par minute
        
        # 1. Enregistrer dans le log
        cursor.execute("""
            INSERT INTO log_vehicules (
                id_vehicule_original, matricule, type_vehicule, date_entrer, 
                date_sortie, duree_jours, duree_minutes, montant_total, 
                id_place, id_admin, image_path, action_type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            vehicule['id_vehicule'], vehicule['matricule'], vehicule['type_vehicule'],
            vehicule['date_entrer'], date_sortie, jours, total_minutes, montant,
            vehicule['id_place'], vehicule['id_admin'], vehicule.get('image_path', None), 'SORTIE'
        ))
        
        # 2. Libérer la place
        if vehicule['id_place']:
            cursor.execute("""
                UPDATE places 
                SET etat = 0, id_vehicule = NULL, id_admin = NULL, id_ticket = NULL
                WHERE id_place = %s
            """, (vehicule['id_place'],))
        
        # 3. Marquer le véhicule comme sorti au lieu de le supprimer
        cursor.execute("""
            UPDATE vehicule 
            SET date_sortie = %s, id_place = NULL, id_ticket = NULL
            WHERE id_vehicule = %s
        """, (date_sortie, vehicule_id))
        
        db.commit()
        
        # Notification de succès
        print(f"Sortie du véhicule {vehicule_id} enregistrée")
        
        return jsonify({'success': True, 'message': f'Sortie enregistrée avec succès. Montant: {montant:.2f}€'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/generate_exit_ticket/<int:vehicule_id>', methods=['POST'])
def generate_exit_ticket(vehicule_id):
    """Route pour générer le ticket de sortie"""
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'})
    
    try:
        # Récupérer les informations du véhicule depuis le log
        cursor.execute("""
            SELECT * FROM log_vehicules WHERE id_vehicule_original = %s
        """, (vehicule_id,))
        vehicule = cursor.fetchone()
        
        if not vehicule:
            return jsonify({'success': False, 'message': 'Véhicule non trouvé dans les logs'})
        
        # Utiliser les données calculées du log
        jours = vehicule['duree_jours']
        heures = vehicule['duree_heures']
        minutes = vehicule['duree_minutes']
        secondes = vehicule['duree_secondes']
        montant = vehicule['montant_total']
        
        # Calculer le total des minutes pour l'affichage
        total_minutes = (jours * 24 * 60) + (heures * 60) + minutes
        if secondes > 0:
            total_minutes += 1
        
        # Tarif par minute
        TARIFF_PER_MINUTE = 0.5
        
        # Générer le contenu du ticket
        # Gérer les dates qui peuvent être None
        date_entree_str = vehicule['date_entrer'].strftime('%d/%m/%Y') if vehicule['date_entrer'] else 'N/A'
        date_sortie_str = vehicule['date_sortie'].strftime('%d/%m/%Y') if vehicule['date_sortie'] else 'N/A'
        
        ticket_content = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        TICKET DE SORTIE                                       ║
║                    SafeParkX - Système Automatique                            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  🎫 NUMÉRO DE TICKET: {vehicule.get('id_ticket', 'N/A')}                      ║
║  🚗 MATRICULE: {vehicule['matricule']}                                        ║
║  🚙 TYPE DE VÉHICULE: {vehicule['type_vehicule']}                             ║
║  🅿️  PLACE ASSIGNÉE: {vehicule.get('id_place', 'N/A')}                        ║
║  📅 DATE D'ENTRÉE: {date_entree_str}                                         ║
║  📅 DATE DE SORTIE: {date_sortie_str}                                        ║
║  ⏱️  DURÉE TOTALE: {jours}j {heures:02d}h {minutes:02d}m {secondes:02d}s     ║
║  💰 MONTANT À PAYER: {montant:.2f} DH ({total_minutes} min × {TARIFF_PER_MINUTE} DH/min) ║
║  👤 ADMIN: {vehicule['id_admin']:03d}                                         ║
║                                                                               ║
║  ⚠️  IMPORTANT:                                                               ║
║  • Merci d'avoir utilisé nos services                                        ║
║  • Paiement effectué à la sortie                                             ║
║  • À bientôt !                                                               ║
║                                                                               ║
║  📞 CONTACT: deweb TECHNOLOGY                                                 ║
║  🌐 WWW.SAFEPARKX.COM | www.deweb.ma                                         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """
        
        # Créer le dossier tickets s'il n'existe pas
        tickets_folder = 'static/tickets'
        if not os.path.exists(tickets_folder):
            os.makedirs(tickets_folder)
        
        # Générer le nom du fichier ticket
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ticket_filename = f'ticket_sortie_{vehicule["matricule"]}_{timestamp}.txt'
        ticket_filepath = os.path.join(tickets_folder, ticket_filename)
        
        # Écrire le contenu du ticket
        with open(ticket_filepath, 'w', encoding='utf-8') as f:
            f.write(ticket_content)
        
        # Retourner le fichier
        return send_file(ticket_filepath, as_attachment=True, download_name=ticket_filename)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/delete_capture/<filename>', methods=['DELETE'])
def delete_capture(filename):
    """Route pour supprimer une capture"""
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'})
    
    try:
        filepath = os.path.join(capture_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            # Notification de succès
            print(f"Capture {filename} supprimée")
            return jsonify({'success': True, 'message': 'Capture supprimée avec succès'})
        else:
            return jsonify({'success': False, 'message': 'Fichier non trouvé'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

# Routes SocketIO simplifiées
@socketio.on('connect')
def handle_connect():
    """Gestion de la connexion SocketIO"""
    print('Client connecté')
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Gestion de la déconnexion SocketIO"""
    print('Client déconnecté')





if __name__ == '__main__':
    try:
        # Initialiser la connexion à la base de données
        reset_database_connection()
        
        print("🚀 Application SafeParkX démarrée!")
        
        socketio.run(app, debug=True, host='0.0.0.0', port=5001)
    finally:
        release_camera()
