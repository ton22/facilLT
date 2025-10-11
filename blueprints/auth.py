from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    from validation import FormValidator, flash_validation_errors, get_validation_errors_for_template
    
    if request.method == 'POST':
        nome = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        
        # Validar campos obrigatórios
        validation_result = FormValidator.validate_required(nome, "Nome de usuário")
        senha_validation = FormValidator.validate_required(senha, "Senha")
        
        if not senha_validation.is_valid:
            validation_result.errors.extend(senha_validation.errors)
            validation_result.is_valid = False
        
        if not validation_result.is_valid:
            flash_validation_errors(validation_result)
            return render_template('login.html', 
                                 validation_errors=get_validation_errors_for_template(validation_result))
        
        usuario = Usuario.query.filter_by(nome=nome).first()
        
        if not usuario:
            validation_result.add_error("usuario", "Usuário não encontrado")
            flash_validation_errors(validation_result)
            return render_template('login.html', 
                                 validation_errors=get_validation_errors_for_template(validation_result))
        
        if not check_password_hash(usuario.senha, senha):
            validation_result.add_error("senha", "Senha incorreta")
            flash_validation_errors(validation_result)
            return render_template('login.html', 
                                 validation_errors=get_validation_errors_for_template(validation_result))
        
        if not usuario.aprovado:
            flash('Usuário não aprovado pelo administrador.', 'warning')
            return render_template('login.html')
        
        session['usuario'] = usuario.nome
        session['tipo'] = usuario.tipo
        usuario.ultimo_acesso = datetime.utcnow()
        db.session.commit()
        flash('Login realizado com sucesso!', 'success')
        return redirect(url_for('index'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('tipo', None)
    return redirect(url_for('auth.login'))

@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    from validation import FormValidator, flash_validation_errors, get_validation_errors_for_template
    
    if request.method == 'POST':
        nome = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        
        # Validar nome de usuário
        validation_result = FormValidator.validate_username(nome)
        
        # Validar senha
        password_validation = FormValidator.validate_password_strength(senha)
        if not password_validation.is_valid:
            validation_result.errors.extend(password_validation.errors)
            validation_result.is_valid = False
        
        # Validar confirmação de senha
        if senha != confirmar_senha:
            validation_result.add_error("confirmar_senha", "Confirmação de senha não confere")
        
        # Verificar se o usuário já existe
        if nome:
            usuario_existente = Usuario.query.filter_by(nome=nome).first()
            if usuario_existente:
                validation_result.add_error("usuario", "Nome de usuário já existe")
        
        if not validation_result.is_valid:
            flash_validation_errors(validation_result)
            return render_template('cadastro.html', 
                                 validation_errors=get_validation_errors_for_template(validation_result))
        
        try:
            # Criar novo usuário
            hash_senha = generate_password_hash(senha)
            novo_usuario = Usuario(nome=nome, senha=hash_senha, tipo='apostador', aprovado=False)
            db.session.add(novo_usuario)
            db.session.commit()
            flash('Cadastro realizado com sucesso! Aguarde a aprovação do administrador.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Erro ao cadastrar usuário: {str(e)}', 'error')
            return render_template('cadastro.html')
    
    return render_template('cadastro.html')