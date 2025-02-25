from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
import random
from datetime import datetime
import os
from flask import request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask import send_from_directory
from datetime import datetime, timedelta
from flask import request, jsonify
from flask import make_response
import uuid

from dateutil.relativedelta import relativedelta  # Importar relativedelta para manejar fechas con meses

app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mi_clave_secreta'
app.config['UPLOAD_FOLDER'] = 'static/uploads/receipts'

# Extensiones permitidas para los archivos subidos
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


# Inicializar la base de datos
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.String(5), primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    family_phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)  # Nuevo campo para ciudad
    dob = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    doc_type = db.Column(db.String(20), nullable=False)
    doc_number = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    front_image_path = db.Column(db.String(200), nullable=True)
    back_image_path = db.Column(db.String(200), nullable=True)
    signature_path = db.Column(db.String(200), nullable=True)
    signature = db.Column(db.Text, nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_pending = db.Column(db.Boolean, default=False, nullable=False)
    balance = db.Column(db.Float, default=0.0, nullable=False)
    role = db.Column(db.String(50), nullable=False, default='User regular')
    receipt_url = db.Column(db.String(500), nullable=True)
    payment_method = db.Column(db.String(20), nullable=True)
    payment_number = db.Column(db.String(50), nullable=True)
    whatsapp = db.Column(db.String(50), nullable=True)  # Asegúrate de que este campo esté definido


    def __repr__(self):
        return f"<User {self.first_name} {self.last_name}>"

    def set_password(self, password):
        """Método para encriptar la contraseña del usuario."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Método para verificar la contraseña del usuario."""
        return check_password_hash(self.password, password)



class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(5), db.ForeignKey('user.id'), nullable=False)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan_application.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_details = db.Column(db.String(255), nullable=False)
    loan_name = db.Column(db.String(255), nullable=False)
    loan_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pendiente')  # Estado del pago: pendiente, aprobado, rechazado
    receipt_url = db.Column(db.String(500), nullable=True)  # Agrega este campo

    user = db.relationship('User', backref=db.backref('payments', lazy=True))
    loan = db.relationship('LoanApplication', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f"<Payment {self.id} for Loan {self.loan_id} by User {self.user_id}>"


class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(5), db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    payment_option = db.Column(db.String(50), nullable=False)
    total_with_costs = db.Column(db.Integer, nullable=False)
    installments = db.Column(db.Integer, nullable=False)
    installment_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pendiente')
    payment_dates = db.Column(db.PickleType, nullable=True)  # Nueva columna para fechas de pago

    user = db.relationship('User', backref=db.backref('loan_applications', lazy=True))

    def __repr__(self):
        return f"<LoanApplication {self.id} for User {self.user_id}>"



    def __repr__(self):
        return f"<User {self.first_name} {self.last_name}>"

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(5), db.ForeignKey('user.id'), nullable=False)  # Referencia al usuario que hace la referencia
    friend_name = db.Column(db.String(255), nullable=False)  # Nombre del amigo o cliente referido
    friend_whatsapp = db.Column(db.String(50), nullable=False)  # Número de WhatsApp del referido
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha de creación del registro
    whatsapp = db.Column(db.String(50), nullable=True)  # Agregar el campo whatsapp aquí
    friend_id = db.Column(db.String(36), unique=True, nullable=False)  # Campo para almacenar el ID único

    user = db.relationship('User', backref=db.backref('referrals', lazy=True))  # Relación con el usuario que hace la referencia

    def __repr__(self):
        return f"<Referral {self.id} by User {self.user_id}>"

# Crear las tablas si no existen
with app.app_context():
    db.create_all()


# Función para verificar las extensiones permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Verificar si la carpeta de recibos existe, si no, crearla
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Ruta para servir los archivos de recibo
@app.route('/uploads/receipts/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Crear las tablas si no existen
with app.app_context():
    db.create_all()



@app.route('/approve_payment/<int:payment_id>', methods=['POST'])
def approve_payment(payment_id):
    payment = Payment.query.get(payment_id)
    if payment:
        # Actualizar el estado del pago
        payment.status = 'aprobado'
        
        # Obtener el usuario relacionado con el pago
        user = User.query.get(payment.user_id)
        if user:
            # Restar el monto del pago del balance del usuario
            user.balance -= payment.amount
            db.session.commit()  # Guardar los cambios en la base de datos
        
        db.session.commit()  # Guardar el cambio del pago aprobado
    
    # Redirigir al dashboard o la página deseada después de aprobar el pago
    return redirect(url_for('dashboard'))

@app.route('/reject_payment/<int:payment_id>', methods=['POST'])
def reject_payment(payment_id):
    payment = Payment.query.get(payment_id)
    if payment:
        payment.status = 'rechazado'
        db.session.commit()
    # No hay mensaje flash, simplemente redirige
    return redirect(url_for('dashboard'))  # Redirige al dashboard o página que desees


@app.route('/submit_payment', methods=['POST'])
def submit_payment():
    # Obtener los datos del formulario
    user_id = request.form.get('user_id')
    loan_id = request.form.get('loan_id')
    loan_amount = request.form.get('loan_amount')
    loan_name = request.form.get('loan_name')
    loan_date = request.form.get('loan_date')
    payment_method = request.form.get('payment_method')
    payment_details = request.form.get('payment_details')

    # Verificar si el archivo del comprobante de pago está presente en la solicitud
    if 'payment_receipt' not in request.files:
        return redirect(url_for('home'))  # Redirigir al dashboard

    file = request.files['payment_receipt']

    # Verificar si el archivo tiene un nombre
    if file.filename == '':
        return redirect(url_for('home'))  # Redirigir al dashboard

    # Si el archivo es válido, procesarlo
    if file and allowed_file(file.filename):
        # Usar secure_filename para asegurar que el nombre del archivo sea seguro
        filename = secure_filename(file.filename)
        
        # Crear un nombre único para el archivo: userID_loanID_payment.jpg
        unique_filename = f"{user_id}_{loan_id}_payment_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{filename.rsplit('.', 1)[1].lower()}"
        
        # Crear una ruta única para el archivo (ruta relativa)
        file_path = os.path.join('uploads/receipts', unique_filename).replace("\\", "/")

        # Guardar el archivo en el servidor
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        # Crear una nueva entrada de pago en la base de datos
        loan_date = datetime.strptime(loan_date, '%Y-%m-%d').date()

        # Verificar si ya existe un pago para esta cuota
        payment_for_loan = Payment.query.filter_by(user_id=user_id, loan_id=loan_id).first()

        if payment_for_loan:
            # Si el pago anterior está en "rechazado", actualizarlo a "pendiente"
            if payment_for_loan.status == 'rechazado':
                payment_for_loan.status = 'pendiente'
                db.session.commit()  # Guardar el cambio en el estado del pago anterior

        # Crear un nuevo pago para la cuota
        new_payment = Payment(
            user_id=user_id,
            loan_id=loan_id,
            amount=float(loan_amount.replace('$', '').replace(',', '')),  # Asegúrate de convertir el monto correctamente
            payment_method=payment_method,
            payment_details=payment_details,
            loan_name=loan_name,  # Guardamos el nombre de la cuota
            loan_date=loan_date,  # Guardamos la fecha de la cuota
            receipt_url=file_path  # Guardamos la ruta relativa del comprobante en la base de datos
        )

        # Guardar el pago en la base de datos
        db.session.add(new_payment)
        db.session.commit()

        # Obtener el usuario para mostrar su nombre y apellido
        user = User.query.get(user_id)
        if user:
            user_full_name = f"{user.first_name} {user.last_name}"
        else:
            user_full_name = "Usuario desconocido"

        # Notificación en el Dashboard: El usuario ha realizado un pago
        flash(f"El usuario {user_full_name} (ID: {user_id}) ha realizado un pago de {loan_amount} para el préstamo '{loan_name}'", "success")
    
    # Redirigir al dashboard
    return redirect(url_for('home'))


@app.route('/refer_friend', methods=['POST'])
def refer_friend():
    # Obtener los datos del formulario
    friend_name = request.form.get('friend_name')
    friend_whatsapp = request.form.get('friend_whatsapp')
    user_id = session['user_id']  # Obtener el ID del usuario actual desde la sesión

    # Verificar que los datos no estén vacíos
    if not friend_name or not friend_whatsapp:
        return redirect(url_for('home'))

    # Obtener el nombre del usuario que hace la referencia
    user = User.query.get(user_id)

    # Crear un ID único para el referido
    referred_id = str(uuid.uuid4())  # Genera un ID único para el referido

    # Crear una nueva entrada en el modelo Referral
    new_referral = Referral(
        user_id=user_id,  # El ID del usuario que hace la referencia
        friend_name=friend_name,
        friend_whatsapp=friend_whatsapp,
        friend_id=referred_id  # Guardar el ID único del referido
    )

    # Guardar la referencia en la base de datos
    db.session.add(new_referral)
    db.session.commit()

    # Mensaje flash con los datos de la referencia
    flash(f"El usuario {user.first_name} {user.last_name} ha referido a {friend_name} con el número {friend_whatsapp}.", "success")
    
    return redirect(url_for('home'))


@app.route('/referidos', methods=['GET'])
def get_referred_friends():
    # Obtener todos los referidos y los usuarios relacionados, ordenados por la fecha de creación (más recientes primero)
    referrals = db.session.query(Referral, User).join(User, User.id == Referral.user_id).order_by(Referral.created_at.desc()).all()

    # Crear una lista con la información de los referidos y el que los refirió
    referred_data = [
        {
            'referidor': {
                'nombre': user.first_name,
                'whatsapp': user.whatsapp  # Ahora tenemos los datos del usuario directamente
            },
            'referido': {
                'id': referral.friend_id,  # Aquí agregamos el ID único del referido
                'nombre': referral.friend_name,
                'whatsapp': referral.friend_whatsapp,
                'fecha_referido': referral.created_at.strftime('%Y-%m-%d %H:%M:%S')  # Formateamos la fecha y hora
            }
        }
        for referral, user in referrals
    ]

    # Retornar los datos en formato JSON
    return jsonify({"referidos": referred_data}), 200

@app.route('/')
def index():
    # Verificar si el usuario está autenticado
    if 'user_id' in session:
        # Obtener el usuario correspondiente al ID almacenado en la sesión
        user = User.query.get(session['user_id'])
        
        # Si no se encuentra un usuario con ese ID, eliminar el ID de la sesión
        if user is None:
            session.pop('user_id', None)  # Eliminar user_id de la sesión
            return redirect(url_for('index'))  # Redirigir al inicio para que el usuario se loguee o registre

        # Si el usuario está autenticado y existe en la base de datos, redirigir a home
        return redirect(url_for('home'))  # Redirigir al home si ya está logueado

    return render_template('index.html')  # Si no está logueado, mostrar el formulario de registro

@app.route('/register', methods=['POST'])
def register():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email').lower()  # Convertir a minúsculas
    phone = request.form.get('phone')
    family_phone = request.form.get('family_phone')
    address = request.form.get('address')
    city = request.form.get('city')  # Obtener la ciudad
    dob_str = request.form.get('dob')
    doc_type = request.form.get('doc_type')
    doc_number = request.form.get('doc_number')
    password = request.form.get('password')
    gender = request.form.get('gender')
    payment_method = request.form.get('payment_method')
    payment_number = request.form.get('payment_number')

    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    hashed_password = generate_password_hash(password)

    # Verificar si el correo ya existe en la base de datos
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Este correo ya está registrado. Intenta con otro."})

    # Asignar el rol según el correo electrónico
    if email == 'admin@gmail.com':
        role = 'Admin'
    else:
        role = 'User regular'

    # Crear el nuevo usuario con el campo de ciudad y el rol
    user_id = str(random.randint(10000, 99999))  # Generación de ID aleatorio
    new_user = User(
        id=user_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        family_phone=family_phone,
        address=address,
        city=city,  # Almacenar la ciudad
        dob=dob,
        doc_type=doc_type,
        doc_number=doc_number,
        password=hashed_password,
        gender=gender,
        role=role,  # Asignar el rol aquí
        payment_method=payment_method,
        payment_number=payment_number
    )

    db.session.add(new_user)
    db.session.commit()

    # Redirigir a la página de éxito sin enviar mensaje JSON
    return redirect(url_for('register_success'))


def get_total_users():
    return User.query.count()
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%m/%d/%Y'):
    if isinstance(value, datetime):
        return value.strftime(format)
    return value


@app.route('/dashboard')
def dashboard():
    # Verificamos que el usuario esté autenticado y sea User regular
    if 'user_id' in session and session['user_role'] == 'Admin':
        # Obtener todos los usuarios
        users = User.query.all()

        # Obtener el total de usuarios
        total_users = get_total_users()  # Llamada a la función para obtener el total de usuarios

        # Obtener las solicitudes de préstamos de todos los usuarios
        loan_applications = LoanApplication.query.all()

        payments = Payment.query.all()

        # Convertir las fechas de las solicitudes de préstamo a datetime
        current_date = datetime.now()
        for loan in loan_applications:
            loan.remaining_days = []  # Inicializamos el campo remaining_days como lista vacía
            if loan.payment_dates:
                loan.payment_dates = [datetime.strptime(date_str, '%Y-%m-%d') for date_str in loan.payment_dates]
                # Calcular los días restantes para cada fecha de pago
                for payment_date in loan.payment_dates:
                    days_left = (payment_date - current_date).days
                    loan.remaining_days.append(days_left)
            else:
                loan.payment_dates = []

        # Pasar la información a la plantilla
        return render_template('dashboard.html', users=users, total_users=total_users, loan_applications=loan_applications, payments=payments)
    else:
        return redirect(url_for('home'))  # Si no es admin o no está autenticado, redirigimos al inicio


@app.route('/approve_verification/<user_id>', methods=['POST'])
def approve_verification(user_id):
    user = User.query.get(user_id)
    if user:
        user.is_verified = True
        user.verification_pending = False
        db.session.commit()
    return redirect(url_for('dashboard'))  # Redirigir al dashboard después de aprobar


@app.route('/reject_verification/<user_id>', methods=['POST'])
def reject_verification(user_id):
    user = User.query.get(user_id)
    if user:
        user.verification_pending = False
        db.session.commit()
    return redirect(url_for('dashboard'))  # Redirigir al dashboard después de rechazar



# Ruta de éxito después de registro
@app.route('/register_success')
def register_success():
    return render_template('register_success.html')
@app.route('/login', methods=['POST'])
def login():
    # Recibiendo datos del formulario
    email = request.form.get('email').lower()  # Convertir a minúsculas
    password = request.form.get('password')

    # Buscar el usuario por correo electrónico
    user = User.query.filter_by(email=email).first()

    if not user:
        # Si el usuario no existe, mensaje de error para correo
        return jsonify({'error': "El correo electrónico no está registrado."}), 400  # Establecer código de error 400
    elif not user.check_password(password):
        # Si la contraseña es incorrecta, mensaje de error para contraseña
        return jsonify({'error': "Contraseña incorrecta."}), 400  # Establecer código de error 400
    else:
        # Si el usuario existe y la contraseña es correcta
        session['user_id'] = user.id  # Guardamos el ID del usuario en la sesión
        session['user_role'] = user.role  # Guardamos el rol del usuario en la sesión
        return jsonify({'success': True, 'redirect': url_for('home')})




@app.route('/home')
def home():
    # Verificar si el usuario está autenticado
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirigir al login si no está autenticado

    # Obtener el usuario autenticado desde la base de datos
    user = User.query.get(session['user_id'])

    # Verificar si el usuario tiene rol de 'Admin'
    if user.role == 'Admin':
        return redirect(url_for('dashboard'))  # Redirigir al dashboard si es Admin

    # Obtener las solicitudes de crédito asociadas al usuario
    loans = LoanApplication.query.filter_by(user_id=user.id).all()
    
    # Obtener los pagos realizados por el usuario
    payments = Payment.query.filter_by(user_id=user.id).all()

    # Pasar la información del usuario, préstamos y pagos a la plantilla
    return render_template('home.html', user=user, loans=loans, payments=payments)



@app.route('/creditapp')
def creditapp():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Si no está autenticado, redirigir al login

    # Obtener el usuario autenticado
    user = User.query.get(session['user_id'])

    # Verificar si el usuario está verificado
    if not user.is_verified:
        return redirect(url_for('account'))  # Redirigir a la página de cuenta o donde quieras mostrar el mensaje

    # Obtener las solicitudes de préstamo del usuario
    loan_applications = LoanApplication.query.filter_by(user_id=user.id).all()

    # Pasar tanto el usuario como las solicitudes de préstamo a la plantilla
    return render_template('creditapp.html', user=user, loan_applications=loan_applications)  # Página de aplicación de crédito


@app.route('/loans_with_remaining_days')
def loans_with_remaining_days():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Si no está autenticado, redirigir al login

    # Obtener el usuario autenticado
    user = User.query.get(session['user_id'])

    # Obtener los préstamos aprobados del usuario
    loans = LoanApplication.query.filter_by(user_id=user.id, status='aprobado').all()

    # Calcular los días restantes para cada cuota
    loans_with_remaining_days = []
    current_date = datetime.now()

    for loan in loans:
        remaining_days = []
        for payment_date_str in loan.payment_dates:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
            days_left = (payment_date - current_date).days  # Calcular la diferencia en días
            remaining_days.append(days_left)
        
        loans_with_remaining_days.append({
            'loan': loan,
            'remaining_days': remaining_days
        })

    # Pasar los préstamos con los días restantes a la plantilla
    return render_template('loans_with_remaining_days.html', loans_with_remaining_days=loans_with_remaining_days)

@app.route('/change_role/<user_id>', methods=['POST'])
def change_role(user_id):
    # Verificar si el usuario tiene permisos de admin
    if 'user_id' in session and session['user_role'] == 'Admin':
        # Obtener el usuario de la base de datos
        user = User.query.get(user_id)
        
        if user:
            # Obtener el nuevo rol del formulario
            new_role = request.form.get('role')
            
            # Verificar si el rol es válido (solo Admin y User Regular)
            if new_role in ['Admin', 'User regular']:
                user.role = new_role  # Cambiar el rol
                db.session.commit()  # Guardar cambios en la base de datos
                flash(f"El rol del usuario {user.first_name} {user.last_name} ha sido cambiado a {new_role}.", "success")
        else:
            flash("Usuario no encontrado.", "danger")
    
    return redirect(url_for('dashboard'))  # Redirigir al dashboard

@app.errorhandler(500)
def internal_error(error):
    return render_template('error500.html'), 500


@app.route('/submit_loan_application', methods=['POST'])
def submit_loan_application():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Si no está autenticado, redirigir al login

    # Obtener los datos del formulario
    amount = request.form['amount']
    payment_option = request.form['payment_option']
    total_with_costs = request.form['total_with_costs']
    installments = request.form['installments']

    # Convertir a números (float para total_with_costs y int para installments)
    total_with_costs = float(total_with_costs)  # Asegurarte de convertirlo a float
    installments = int(installments)  # Asegurarte de convertirlo a int

    # Calcular las cuotas basadas en el total con costos
    installment_amount = total_with_costs / installments  # Monto por cuota

    # Obtener el usuario autenticado
    user = User.query.get(session['user_id'])

    # Crear una nueva solicitud de préstamo
    new_loan_application = LoanApplication(
        user_id=user.id,
        amount=amount,
        payment_option=payment_option,
        total_with_costs=total_with_costs,
        installments=installments,
        installment_amount=installment_amount
    )

    # Agregar la solicitud a la base de datos
    db.session.add(new_loan_application)
    db.session.commit()

    flash(f"El usuario {user.first_name} {user.last_name} ha solicitado un préstamo de {amount} con {installments} cuotas.", 'success')
    return redirect(url_for('loan_submission_success'))  # Redirigir al usuario a la página de aplicación



@app.route('/loan_submission_success')
def loan_submission_success():
    # Obtener el usuario autenticado
    user = User.query.get(session['user_id'])

    # Obtener la última solicitud de préstamo del usuario
    loan_application = LoanApplication.query.filter_by(user_id=user.id).order_by(LoanApplication.id.desc()).first()

    if loan_application:
        # Pasar tanto 'loan' como 'user' a la plantilla
        return render_template('loan_submission_success.html', loan=loan_application, user=user)
    else:
        # Redirigir o mostrar mensaje de error si no hay solicitud
        return redirect(url_for('creditapp'))


@app.route('/upload_documents', methods=['POST'])
def upload_documents():
    if 'user_id' not in session:
        flash("Debes estar logueado para cargar documentos.", "danger")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Verificar si el formulario tiene archivos
    front_image = request.files.get('frontImage')
    back_image = request.files.get('backImage')
    signature_image = request.files.get('signatureImage')  # Imagen de la firma

    # Función para generar un nombre único para cada archivo basado en el user_id
    def generate_unique_filename(filename, user_id):
        # Genera un nombre único para el archivo utilizando el user_id y el nombre original
        name, ext = os.path.splitext(filename)
        unique_filename = f"{user_id}_{name}{ext}"
        return unique_filename

    # Verificar si se cargó la imagen del frente
    if front_image and allowed_file(front_image.filename):
        front_filename = generate_unique_filename(front_image.filename, user.id)
        front_image_path = os.path.join(app.config['UPLOAD_FOLDER'], front_filename)
        front_image.save(front_image_path)
    else:
        return redirect(url_for('account'))  # Redirigir al formulario de cuenta

    # Verificar si se cargó la imagen del reverso
    if back_image and allowed_file(back_image.filename):
        back_filename = generate_unique_filename(back_image.filename, user.id)
        back_image_path = os.path.join(app.config['UPLOAD_FOLDER'], back_filename)
        back_image.save(back_image_path)
    else:
        return redirect(url_for('account'))  # Redirigir al formulario de cuenta

    # Verificar si se cargó la imagen de la firma
    if signature_image and allowed_file(signature_image.filename):
        signature_filename = generate_unique_filename(signature_image.filename, user.id)
        signature_image_path = os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)
        signature_image.save(signature_image_path)
    else:
        return redirect(url_for('account'))  # Redirigir al formulario de cuenta

    # Guardar las rutas de las imágenes y la firma en la base de datos
    user.front_image_path = f"/uploads/receipts/{front_filename}"
    user.back_image_path = f"/uploads/receipts/{back_filename}"
    user.signature_path = f"/uploads/receipts/{signature_filename}"  # Guardar la ruta de la imagen de la firma
    user.signature = request.form.get('signature')  # Si se guarda la firma como base64

    # Marcar como pendiente la verificación
    user.verification_pending = True

    db.session.commit()

    # Mensaje indicando que el usuario ha subido los documentos para verificación
    flash(f"El usuario {user.first_name} {user.last_name} ha subido documentos para la verificación de cuenta.", "success")
    return redirect(url_for('account'))  # Redirigir a la página de cuenta


@app.route('/approve_loan/<int:loan_id>', methods=['POST'])
def approve_loan(loan_id):
    loan = LoanApplication.query.get(loan_id)
    if loan and loan.status == 'pendiente':
        # Actualizamos el balance del usuario
        user = User.query.get(loan.user_id)
        user.balance += loan.total_with_costs  # Asignamos el total con costos al balance del usuario

        loan.status = 'aprobado'  # Actualizamos el estado del préstamo
        
        # Calcular las fechas de pago
        payment_dates = []
        current_date = datetime.now()  # Fecha actual
        payment_option = loan.payment_option  # Suponemos que esta es la opción de pago seleccionada en el préstamo

        if payment_option == 'Mensual':
            # Sumar un mes completo por cada cuota
            for i in range(loan.installments):
                payment_date = current_date + relativedelta(months=i+1)  # Sumar un mes completo
                payment_dates.append(payment_date.strftime('%Y-%m-%d'))

        elif payment_option == 'Quincenal':
            payment_date = current_date + timedelta(days=15)  # Primera cuota 15 días después de la fecha de aprobación
            for i in range(loan.installments):
                payment_dates.append(payment_date.strftime('%Y-%m-%d'))  # Guardamos la fecha de pago actual
                payment_date += timedelta(days=15)  # Sumamos 15 días para la siguiente cuota

        elif payment_option == 'Semanal':
            # Sumar una semana por cada cuota (semanal)
            for i in range(loan.installments):
                payment_date = current_date + timedelta(weeks=i+1)  # Semana por cuota
                payment_dates.append(payment_date.strftime('%Y-%m-%d'))

        elif payment_option == '6 Semanas':
            # Sumar 1 semana por cada cuota (6 cuotas)
            payment_date = current_date + timedelta(weeks=1)  # Primera cuota 1 semana después de la fecha de aprobación
            for i in range(loan.installments):
                payment_dates.append(payment_date.strftime('%Y-%m-%d'))  # Guardamos la fecha de pago actual
                payment_date += timedelta(weeks=1)  # Sumamos 1 semana para la siguiente cuota

        elif payment_option == '8 Semanas':
            # Sumar 1 semana por cada cuota (8 cuotas)
            payment_date = current_date + timedelta(weeks=1)  # Primera cuota 1 semana después de la fecha de aprobación
            for i in range(loan.installments):
                payment_dates.append(payment_date.strftime('%Y-%m-%d'))  # Guardamos la fecha de pago actual
                payment_date += timedelta(weeks=1)  # Sumamos 1 semana para la siguiente cuota

        loan.payment_dates = payment_dates  # Guardamos las fechas de pago en el préstamo
        
        db.session.commit()  # Guardamos los cambios en la base de datos

        return redirect(url_for('dashboard'))

    return redirect(url_for('dashboard'))



# Ruta para rechazar el crédito
@app.route('/reject_loan/<int:loan_id>', methods=['POST'])
def reject_loan(loan_id):
    loan_application = LoanApplication.query.get(loan_id)
    if loan_application:
        loan_application.status = 'rechazado'  # Cambiar el estado a rechazado
        db.session.commit()
    return redirect(url_for('dashboard'))  # Redirigir al dashboard después de rechazar el préstamo


@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Si no está autenticado, redirigir al login

    # Obtener el usuario autenticado
    user = User.query.get(session['user_id'])

    # Obtener los referidos del usuario autenticado
    referrals = user.referrals  # Los referidos asociados con el usuario

    # Pasar la información del usuario y los referidos a la plantilla
    return render_template('account.html', user=user, referrals=referrals)  # Página de la cuenta del usuario

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Si no está autenticado, redirigir al login

    user = User.query.get(session['user_id'])  # Obtener el usuario autenticado
    
    if request.method == 'POST':
        current_password = request.form.get('currentPassword')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')

        # Verificar si la contraseña actual es correcta
        if not user.check_password(current_password):
            return redirect(url_for('account'))  # Redirigir a la página de cuenta

        # Verificar si la nueva contraseña y la confirmación coinciden
        if new_password != confirm_password:
            return redirect(url_for('account'))  # Redirigir a la página de cuenta

        # Encriptar la nueva contraseña y actualizarla
        user.set_password(new_password)
        db.session.commit()

        flash(f"El usuario {user.first_name} {user.last_name} ha cambiado su contraseña.", "success")
        return redirect(url_for('account'))  # Redirigir a la página de cuenta

    return render_template('account.html', user=user)



@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Elimina el usuario de la sesión
    return redirect(url_for('index'))  # Redirige a la página de inicio

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
