from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['usuario']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario and check_password_hash(usuario.senha, senha):
            if not usuario.aprovado:
                return render_template('login.html', erro="Aguardando aprovação do administrador.")
            session['usuario'] = usuario.nome
            session['tipo'] = usuario.tipo
            # Atualizar último acesso
            usuario.ultimo_acesso = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('index'))
        else:
            return render_template('login.html', erro="Usuário ou senha inválidos.")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('tipo', None)
    return redirect(url_for('auth.login'))

@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['usuario']
        senha = request.form['senha']
        # Verificar se usuário já existe
        if Usuario.query.filter_by(nome=nome).first():
            return render_template('cadastro.html', erro="Nome de usuário já existe.")
        # Criar novo usuário
        hash_senha = generate_password_hash(senha)
        novo_usuario = Usuario(nome=nome, senha=hash_senha, tipo='apostador', aprovado=False)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Cadastro realizado com sucesso! Aguarde a aprovação do administrador.')
        return redirect(url_for('auth.login'))
    return render_template('cadastro.html')