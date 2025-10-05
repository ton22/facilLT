from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(256), nullable=False)  # Aumentado para acomodar hashes mais seguros
    tipo = db.Column(db.String(20), default='apostador')  # 'admin' ou 'apostador'
    aprovado = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime, nullable=True)

class Predicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    numeros = db.Column(db.String(100))
    numeros_json = db.Column(db.Text, nullable=True)
    pontuacao = db.Column(db.Float)
    soma = db.Column(db.Integer, nullable=True)
    primos = db.Column(db.Integer, nullable=True)
    pares = db.Column(db.Integer, nullable=True)
    impares = db.Column(db.Integer, nullable=True)
    chance_media = db.Column(db.Float, nullable=True)
    enviado = db.Column(db.Boolean, default=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

class Sistema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    em_treinamento = db.Column(db.Boolean, default=False)
    ultimo_concurso = db.Column(db.String(20), default='N/A')

# Tabelas relacionadas ao recurso Bolão
class Bolao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    numero_concurso = db.Column(db.String(20), nullable=True)
    data_sorteio = db.Column(db.DateTime, nullable=True)
    resultado_json = db.Column(db.Text, nullable=True)  # lista de 15 ints
    valores_por_pontos_json = db.Column(db.Text, nullable=True)  # mapa {'11': valor, ..., '15': valor}
    criado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    status = db.Column(db.String(20), default='aberto')  # aberto|fechado
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class ConviteBolao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    status = db.Column(db.String(20), default='pendente')  # pendente|aceito|recusado
    jogos_permitidos = db.Column(db.Integer, default=1)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class BolaoJogo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey('bolao.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    numeros_json = db.Column(db.Text, nullable=False)  # lista de 15 ints
    origem_predicao_id = db.Column(db.Integer, db.ForeignKey('predicao.id'), nullable=True)
    pontos = db.Column(db.Integer, nullable=True)
    premio_calculado = db.Column(db.Float, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
