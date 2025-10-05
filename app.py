# # Rota de login
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         nome = request.form['usuario']
#         senha = request.form['senha']
#         usuario = Usuario.query.filter_by(nome=nome).first()
#         if usuario and check_password_hash(usuario.senha, senha):
#             if not usuario.aprovado:
#                 return render_template('login.html', erro="Aguardando aprovação do administrador.")
#             session['usuario'] = usuario.nome
#             session['tipo'] = usuario.tipo
#             return redirect(url_for('index'))
#         else:
#             return render_template('login.html', erro="Usuário ou senha inválidos.")
#     return render_template('login.html')

from flask import Flask, render_template, request, redirect, session, url_for, Response, flash
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, Usuario, Predicao, Sistema, Bolao, ConviteBolao, BolaoJogo
from flask_migrate import Migrate
import lFacil_refatorado_treinamento as treino
import lFacil_refatorado_predicao as predicao
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError
import os
import sqlite3
import ast
import math
import csv
import logging


app = Flask(__name__)
# Usar variável de ambiente para a chave secreta ou gerar uma aleatória
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
# ensure instance folder exists and use absolute path for the SQLite DB
instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(instance_dir, exist_ok=True)
db_file = os.path.join(instance_dir, 'lotofacil.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_file.replace('\\', '/')
# Desativar rastreamento de modificações para melhorar desempenho
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Configurações de segurança
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Inicializar proteção CSRF
csrf = CSRFProtect(app)
# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('app.log'), logging.StreamHandler()]
)
db.init_app(app)
Migrate(app, db)
try:
    from blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
except Exception:
    # Se blueprint não puder ser importado, seguir com rotas locais
    pass




# Rota de perfil do usuário
@app.route('/perfil', methods=['GET'])
def perfil():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    return render_template('perfil.html', usuario=usuario)

@app.route('/historico')
@app.route('/historico/<int:page>')
def historico(page=1):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    # Implementando paginação para melhorar desempenho
    per_page = 10  # Registros por página
    registros = Predicao.query.filter_by(usuario_id=usuario.id).order_by(
        Predicao.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    # lista de bolões disponíveis (simples: todos os bolões abertos)
    bolaos = Bolao.query.order_by(Bolao.criado_em.desc()).all()
    return render_template('historico.html', registros=registros, BolaosQuery=bolaos)

# Decorator para rotas admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('tipo') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Rotas de autenticação estão no blueprint auth (ver blueprints/auth.py)

# Rota para descartar predição
@app.route('/descartar_predicao', methods=['POST'])
def descartar_predicao():
    return redirect(url_for('index'))

# Rota para salvar predição manualmente
@app.route('/salvar_predicao', methods=['POST'])
def salvar_predicao():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    numeros = request.form['numeros']
    pontuacao = request.form['pontuacao']
    # compute derived stats before saving
    try:
        nums = ast.literal_eval(numeros)
        if not isinstance(nums, (list, tuple)):
            nums = [int(x) for x in str(numeros).strip('[]').split(',') if x.strip()]
    except Exception:
        nums = [int(x) for x in str(numeros).strip('[]').split(',') if x.strip()]
    nums = [int(x) for x in nums]
    soma = sum(nums)
    primeset = set([2,3,5,7,11,13,17,19,23])
    primos = sum(1 for n in nums if n in primeset)
    pares = sum(1 for n in nums if n % 2 == 0)
    impares = len(nums) - pares
    # compute chance_media using same heuristics as the client
    try:
        stats = compute_stats()
        sum_score = 0
        for i in range(min(3, len(stats['sum_range_counts']))):
            rng = stats['sum_range_counts'][i]['range']
            a,b = [int(x) for x in rng.split('-')]
            if soma >= a and soma <= b:
                sum_score = 40 - (i * 10)
                break
        common = stats['most_common_primes'][0] if stats['most_common_primes'] else None
        prime_score = 0 if common is None else max(0, 30 - abs(primos - common) * 7)
        commonEven = stats['most_common_evens'][0] if stats['most_common_evens'] else None
        parity_score = 0 if commonEven is None else max(0, 30 - abs(pares - commonEven) * 6)
        chance_media = min(100, sum_score + prime_score + parity_score)
    except Exception:
        chance_media = None

    import json
    numeros_list = nums
    numeros_json = json.dumps(numeros_list)
    registro = Predicao(usuario_id=usuario.id, numeros=numeros, numeros_json=numeros_json, pontuacao=pontuacao,
                        soma=soma, primos=primos, pares=pares, impares=impares, chance_media=chance_media)
    db.session.add(registro)
    db.session.commit()
    try:
        compute_stats.cache_clear()
    except Exception:
        pass
    return redirect(url_for('historico'))

# Rota para excluir predição do usuário
@app.route('/excluir_predicao/<int:id>', methods=['POST'])
def excluir_predicao(id):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    pred = Predicao.query.filter_by(id=id, usuario_id=usuario.id).first()
    if pred:
        db.session.delete(pred)
        db.session.commit()
        try:
            compute_stats.cache_clear()
        except Exception:
            pass
    return redirect(url_for('historico'))

with app.app_context():
    # Verificar e atualizar o esquema do banco de dados
    import sqlite3
    conn = sqlite3.connect('instance/lotofacil.db')
    cursor = conn.cursor()
    
    # Verificar se as colunas já existem
    cursor.execute("PRAGMA table_info(usuario)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Adicionar colunas necessárias
    if 'data_criacao' not in columns:
        cursor.execute("ALTER TABLE usuario ADD COLUMN data_criacao TIMESTAMP")
    if 'ultimo_acesso' not in columns:
        cursor.execute("ALTER TABLE usuario ADD COLUMN ultimo_acesso TIMESTAMP")
    
    conn.commit()
    conn.close()
    
    # Continuar com a inicialização normal
    db.create_all()
    if not Sistema.query.first():
        db.session.add(Sistema(em_treinamento=False))
        db.session.commit()
    from werkzeug.security import generate_password_hash
    if not Usuario.query.filter_by(nome='admin').first():
        admin = Usuario(nome='admin', senha=generate_password_hash('admin123'), tipo='admin', aprovado=True)
        db.session.add(admin)
        db.session.commit()

    # Attempt to add new Predicao columns if they do not exist (SQLite ALTER TABLE ADD COLUMN)
    try:
        # prefer direct sqlite3 schema changes to ensure columns exist in the exact DB file
        def ensure_predicao_columns(dbpath):
            conn = sqlite3.connect(dbpath)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(predicao);")
            existing = [r[1] for r in cur.fetchall()]
            alterations = []
            if 'soma' not in existing:
                alterations.append("ALTER TABLE predicao ADD COLUMN soma INTEGER;")
            if 'primos' not in existing:
                alterations.append("ALTER TABLE predicao ADD COLUMN primos INTEGER;")
            if 'pares' not in existing:
                alterations.append("ALTER TABLE predicao ADD COLUMN pares INTEGER;")
            if 'impares' not in existing:
                alterations.append("ALTER TABLE predicao ADD COLUMN impares INTEGER;")
            if 'chance_media' not in existing:
                alterations.append("ALTER TABLE predicao ADD COLUMN chance_media FLOAT;")
            for stmt in alterations:
                try:
                    cur.execute(stmt)
                except Exception:
                    # ignore individual failures but continue
                    pass
            conn.commit()
            conn.close()

        # call ensure on the absolute DB file we set earlier
        ensure_predicao_columns(db_file)
    except Exception:
        pass


from functools import lru_cache

@lru_cache(maxsize=32)
def compute_stats(cache_key=None):
    # O parâmetro cache_key não é usado, mas permite invalidar o cache quando necessário
    # build lightweight stats used by the index heatmap and client-side
    predicoes = Predicao.query.all()
    primes = set([2,3,5,7,11,13,17,19,23])
    prime_count_hist = {}
    prime_number_freq = {}
    even_count_hist = {}
    sum_values = []
    for p in predicoes:
        nums = []
        # leitura robusta dos números (JSON preferido, fallback para string)
        try:
            if getattr(p, 'numeros_json', None):
                import json as _json
                nums = _json.loads(p.numeros_json)
            else:
                raise ValueError('no json')
        except Exception:
            try:
                parsed = ast.literal_eval(p.numeros)
                if isinstance(parsed, (list, tuple)):
                    nums = list(parsed)
                else:
                    nums = [int(x) for x in str(p.numeros).strip('[]').split(',') if x.strip()]
            except Exception:
                try:
                    nums = [int(x) for x in str(p.numeros).strip('[]').split(',') if x.strip()]
                except Exception:
                    nums = []
        nums = [int(x) for x in nums] if nums else []
        if not nums:
            continue
        prime_count = sum(1 for n in nums if n in primes)
        for n in nums:
            if n in primes:
                prime_number_freq[n] = prime_number_freq.get(n, 0) + 1
        even_count = sum(1 for n in nums if n % 2 == 0)
        s = sum(nums)
        sum_values.append(s)
        prime_count_hist[prime_count] = prime_count_hist.get(prime_count, 0) + 1
        even_count_hist[even_count] = even_count_hist.get(even_count, 0) + 1

    most_common_primes = []
    if prime_count_hist:
        max_freq = max(prime_count_hist.values())
        most_common_primes = sorted([(cnt, freq) for cnt, freq in prime_count_hist.items() if freq == max_freq], key=lambda x: -x[1])

    prime_number_list = sorted([{'prime': p, 'count': c} for p, c in prime_number_freq.items()], key=lambda x: x['count'], reverse=True)

    even_count_list = []
    most_common_evens = []
    if even_count_hist:
        even_count_list = sorted([{'pares': cnt, 'vezes': freq} for cnt, freq in even_count_hist.items()], key=lambda x: x['pares'])
        max_freq_e = max(even_count_hist.values())
        most_common_evens = sorted([(cnt, freq) for cnt, freq in even_count_hist.items() if freq == max_freq_e], key=lambda x: -x[1])

    # Use fixed theoretical sum ranges for 15 numbers in 1..25 (15..375)
    # Use narrower bins (width = 10) so Top-10 shows more granular and filled ranges
    sum_range_counts = []
    if sum_values:
        min_possible = 15
        max_possible = 375
        bin_width = 10
        bins = []
        start = min_possible
        while start <= max_possible:
            end = min(start + bin_width - 1, max_possible)
            bins.append((start, end))
            start = end + 1
        bin_counts = [0] * len(bins)
        for s in sum_values:
            s_clamped = max(min_possible, min(max_possible, s))
            idx = min((s_clamped - min_possible) // bin_width, len(bins) - 1)
            bin_counts[idx] += 1
    sum_range_counts = [({'range': f"{b[0]}-{b[1]}", 'count': bin_counts[i]}) for i, b in enumerate(bins)]
    # remove empty bins so Top-10 includes only filled ranges
    sum_range_counts = [r for r in sum_range_counts if r['count'] > 0]
    sum_range_counts = sorted(sum_range_counts, key=lambda x: x['count'], reverse=True)[:10]

    # For client-side and saving heuristics, return only the counts (not tuples)
    return {
        'sum_range_counts': sum_range_counts,
        'most_common_primes': [cnt for cnt, _ in most_common_primes],
        'most_common_evens': [cnt for cnt, _ in most_common_evens],
        'prime_number_list': prime_number_list
    }



@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    if not usuario:
        return redirect(url_for('auth.login'))
    sistema = Sistema.query.first()
    # Dados para os cards
    try:
        total_predicoes = Predicao.query.count()
        total_jogos_usuario = Predicao.query.filter_by(usuario_id=usuario.id).count()
    except OperationalError as oe:
        # schema may be in transition; fallback to zero and continue gracefully
        print('OperationalError while querying Predicao counts:', oe)
        total_predicoes = 0
        total_jogos_usuario = 0
    ultimas_predicoes = Predicao.query.filter_by(usuario_id=usuario.id).order_by(Predicao.id.desc()).limit(5).all()
    # Status do treinamento
    ultimo_concurso = getattr(sistema, 'ultimo_concurso', 'N/A')
    # Estatísticas centralizadas
    stats = compute_stats()
    # Validação extra: garantir que user_type é admin se o usuário for admin
    user_type = usuario.tipo if usuario and usuario.tipo == 'admin' else 'apostador'
    return render_template('index.html', user_type=user_type, em_treinamento=sistema.em_treinamento,
        total_predicoes=total_predicoes, total_jogos_usuario=total_jogos_usuario,
        ultimas_predicoes=ultimas_predicoes, ultimo_concurso=ultimo_concurso, stats=stats)

@app.route('/predicao', methods=['POST'])
def fazer_predicao():
    sistema = Sistema.query.first()
    if sistema.em_treinamento:
        return render_template('index.html', mensagem="Sistema em treinamento. Tente novamente em breve.", user_type=session.get('tipo'), em_treinamento=True, stats=compute_stats())

    try:
        lista_numeros = [int(request.form[f"numero{i}"]) for i in range(1, 16)]
        if len(set(lista_numeros)) != 15 or any(n < 1 or n > 25 for n in lista_numeros):
            raise ValueError("Números inválidos.")
        # If the user provided numbers (manually or via suggestion), evaluate that exact game
        try:
            pontuacao = predicao.avaliar(lista_numeros)
            # compute server-side derived stats so the UI shows chance immediately
            nums = lista_numeros
            soma = sum(nums)
            primeset = set([2,3,5,7,11,13,17,19,23])
            primos = sum(1 for n in nums if n in primeset)
            pares = sum(1 for n in nums if n % 2 == 0)
            impares = len(nums) - pares
            # compute chance_media using same heuristics as in salvar_predicao
            try:
                stats = compute_stats()
                sum_score = 0
                for i in range(min(3, len(stats['sum_range_counts']))):
                    rng = stats['sum_range_counts'][i]['range']
                    a,b = [int(x) for x in rng.split('-')]
                    if soma >= a and soma <= b:
                        sum_score = 40 - (i * 10)
                        break
                common = stats['most_common_primes'][0] if stats['most_common_primes'] else None
                prime_score = 0 if common is None else max(0, 30 - abs(primos - common) * 7)
                commonEven = stats['most_common_evens'][0] if stats['most_common_evens'] else None
                parity_score = 0 if commonEven is None else max(0, 30 - abs(pares - commonEven) * 6)
                chance_media = min(100, sum_score + prime_score + parity_score)
            except Exception:
                chance_media = None

            resultado = {"numeros": lista_numeros, "pontuacao": pontuacao, "soma": soma, "primos": primos, "pares": pares, "impares": impares, "chance_media": chance_media}
        except Exception as e:
            # don't silently replace the user's game with another one.
            # Log the error and show the same numbers with an explanatory message.
            print('Error evaluating provided game:', e)
            resultado = {"numeros": lista_numeros, "pontuacao": None}
            return render_template('index.html', predicao=resultado, mensagem=f"Avaliação falhou: {e}", user_type=session.get('tipo'), em_treinamento=False, stats=compute_stats())
        # Apenas mostra o resultado, não salva automaticamente
        # determine a simple label for the chance to match client coloring
        try:
            score = resultado.get('chance_media')
            if score is None:
                chance_label = None
                chance_score = None
                chance_color = None
            else:
                chance_score = int(round(score))
                if chance_score >= 70:
                    chance_label = 'Alta'
                    chance_color = '#5cb85c'
                elif chance_score >= 40:
                    chance_label = 'Média'
                    chance_color = '#f0ad4e'
                else:
                    chance_label = 'Baixa'
                    chance_color = '#d9534f'
        except Exception:
            chance_label = None
            chance_score = None
            chance_color = None
        return render_template('index.html', predicao=resultado, predicao_chance_label=chance_label, predicao_chance_score=chance_score, predicao_chance_color=chance_color, predicao_soma=resultado.get('soma'), user_type=session.get('tipo'), em_treinamento=False, stats=compute_stats())
    except Exception as e:
        return render_template('index.html', mensagem=f"Erro: {str(e)}", user_type=session.get('tipo'), em_treinamento=False, stats=compute_stats())
    # bloco residual removido
@app.route('/exportar_predicoes')
def exportar_predicoes():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    registros = Predicao.query.filter_by(usuario_id=usuario.id).order_by(Predicao.id.desc()).all()
    formato = request.args.get('formato', 'csv')
    if formato == 'xlsx':
        import io
        import pandas as pd
        df = pd.DataFrame([{ 'id': r.id, 'numeros': r.numeros, 'pontuacao': r.pontuacao, 'data': r.data,
                             'soma': r.soma, 'primos': r.primos, 'pares': r.pares, 'impares': r.impares, 'chance_media': r.chance_media } for r in registros])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return Response(output.read(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={"Content-Disposition": "attachment;filename=historico_predicoes.xlsx"})
    elif formato == 'txt':
        def generate():
            for r in registros:
                yield f"{r.id} - {r.numeros} - {r.pontuacao} - soma:{r.soma} - primos:{r.primos} - pares:{r.pares} - impares:{r.impares} - chance:{r.chance_media} - {r.data}\n"
        return Response(generate(), mimetype='text/plain', headers={"Content-Disposition": "attachment;filename=historico_predicoes.txt"})
    else:
        def generate():
            yield 'id,numeros,pontuacao,soma,primos,pares,impares,chance_media,data\n'
            for r in registros:
                yield f'{r.id},"{r.numeros}",{r.pontuacao},{r.soma},{r.primos},{r.pares},{r.impares},{r.chance_media},{r.data}\n'
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=historico_predicoes.csv"})

# Cadastro movido para blueprint auth

# Logout movido para blueprint auth

@app.route('/aprovar/<int:id>', methods=['POST'])
@admin_required
def aprovar(id):
    usuario = Usuario.query.get(id)
    if usuario:
       usuario.aprovado = True
    db.session.commit()
    return redirect(url_for('painel_admin'))

@app.route('/treinar', methods=['POST'])
@admin_required
def treinar_modelos():
    sistema = Sistema.query.first()
    sistema.em_treinamento = True
    db.session.commit()

    # Call training function and handle different possible return shapes robustly.
    resultado = None
    if hasattr(treino, 'executar_treinamento'):
        try:
            resultado = treino.executar_treinamento()
        except Exception as e:
            # If training itself raised, record message and stop
            sistema.em_treinamento = False
            db.session.commit()
            mensagem = f"Erro durante o treinamento: {e}"
            return render_template('index.html', mensagem=mensagem, user_type='admin', em_treinamento=False, ultimo_concurso=getattr(sistema, 'ultimo_concurso', 'N/A'))
    # Normalize resultado into (mensagem, ultimo_concurso)
    mensagem = "Treinamento concluído."
    ultimo_concurso = getattr(sistema, 'ultimo_concurso', 'N/A')
    if resultado is None:
        # nothing returned from treino
        pass
    elif isinstance(resultado, str):
        mensagem = resultado
    elif isinstance(resultado, (list, tuple)):
        if len(resultado) >= 2:
            # prefer first two values
            mensagem = str(resultado[0])
            ultimo_concurso = str(resultado[1])
        elif len(resultado) == 1:
            mensagem = str(resultado[0])
    else:
        # unexpected type, stringify
        mensagem = str(resultado)

    sistema.em_treinamento = False
    sistema.ultimo_concurso = ultimo_concurso
    db.session.commit()
    return render_template('index.html', mensagem=mensagem, user_type='admin', em_treinamento=False, ultimo_concurso=ultimo_concurso)

@app.route('/admin')
@admin_required
def painel_admin():
    pendentes = Usuario.query.filter_by(aprovado=False).all()
    aprovados = Usuario.query.filter_by(aprovado=True).all()
    bolaos = Bolao.query.order_by(Bolao.criado_em.desc()).all()
    return render_template('admin.html', pendentes=pendentes, aprovados=aprovados, bolaos=bolaos)

# Criar bolão (admin)
@app.route('/admin/bolao/criar', methods=['POST'])
@admin_required
def criar_bolao():
    nome = request.form.get('nome')
    numero_concurso = request.form.get('numero_concurso')
    data_sorteio = request.form.get('data_sorteio')
    from datetime import datetime as _dt
    dt = None
    try:
        if data_sorteio:
            dt = _dt.fromisoformat(data_sorteio)
    except Exception:
        dt = None
    bolao = Bolao(nome=nome, numero_concurso=numero_concurso, data_sorteio=dt, criado_por=Usuario.query.filter_by(nome=session['usuario']).first().id)
    db.session.add(bolao)
    db.session.commit()
    return redirect(url_for('detalhe_bolao', bolao_id=bolao.id))

# Detalhe/gerência de bolão (admin)
@app.route('/admin/bolao/<int:bolao_id>', methods=['GET', 'POST'])
@admin_required
def detalhe_bolao(bolao_id):
    import json
    bolao = Bolao.query.get_or_404(bolao_id)
    # se fechado, não permitir edição
    if request.method == 'POST' and bolao.status == 'fechado':
        return redirect(url_for('painel_admin'))
    if request.method == 'POST':
        # atualizar resultado e valores por pontos
        resultado = request.form.get('resultado')  # ex: "1,2,3,...,15"
        valores_11 = request.form.get('valor_11')
        valores_12 = request.form.get('valor_12')
        valores_13 = request.form.get('valor_13')
        valores_14 = request.form.get('valor_14')
        valores_15 = request.form.get('valor_15')
        # parse resultado
        try:
            lista = [int(x.strip()) for x in resultado.split(',') if x.strip()] if resultado else []
            if len(lista) == 15:
                bolao.resultado_json = json.dumps(lista)
        except Exception:
            pass
        # salvar valores por faixa
        try:
            valores = {
                '11': float(valores_11 or 0),
                '12': float(valores_12 or 0),
                '13': float(valores_13 or 0),
                '14': float(valores_14 or 0),
                '15': float(valores_15 or 0),
            }
            bolao.valores_por_pontos_json = json.dumps(valores)
        except Exception:
            pass
        db.session.commit()
        # recalcular pontos/premios nos jogos do bolão, se houver resultado
        if bolao.resultado_json and bolao.valores_por_pontos_json:
            resultado_nums = json.loads(bolao.resultado_json)
            valores = json.loads(bolao.valores_por_pontos_json)
            jogos = BolaoJogo.query.filter_by(bolao_id=bolao.id).all()
            for j in jogos:
                try:
                    nums = json.loads(j.numeros_json)
                    acertos = len(set(nums) & set(resultado_nums))
                    j.pontos = acertos
                    faixa = str(acertos)
                    j.premio_calculado = float(valores.get(faixa, 0))
                except Exception:
                    j.pontos = None
                    j.premio_calculado = None
            db.session.commit()
            # fechar o bolão após cálculo
            bolao.status = 'fechado'
            db.session.commit()
            return redirect(url_for('painel_admin'))
    # somatórios por faixa
    import json
    soma_por_faixa = {}
    total_por_faixa = {}
    jogos = BolaoJogo.query.filter_by(bolao_id=bolao.id).all()
    for j in jogos:
        if j.pontos is None:
            continue
        key = str(j.pontos)
        total_por_faixa[key] = total_por_faixa.get(key, 0) + 1
        soma_por_faixa[key] = soma_por_faixa.get(key, 0.0) + (j.premio_calculado or 0.0)
    convites = ConviteBolao.query.filter_by(bolao_id=bolao.id).all()
    return render_template('admin_bolao_detalhe.html', bolao=bolao, jogos=jogos, convites=convites, total_por_faixa=total_por_faixa, soma_por_faixa=soma_por_faixa)

# Enviar convite (admin) - convite simples para usuário existente por nome
@app.route('/admin/bolao/<int:bolao_id>/convidar', methods=['POST'])
@admin_required
def convidar_para_bolao(bolao_id):
    usuario_nome = request.form.get('usuario')
    jogos_permitidos = int(request.form.get('jogos_permitidos') or 1)
    usuario = Usuario.query.filter_by(nome=usuario_nome).first()
    if usuario:
        convite = ConviteBolao(bolao_id=bolao_id, usuario_id=usuario.id, jogos_permitidos=jogos_permitidos)
        db.session.add(convite)
        db.session.commit()
    return redirect(url_for('detalhe_bolao', bolao_id=bolao_id))

# Página Bolão (usuário)
@app.route('/bolao')
def pagina_bolao():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    convites = ConviteBolao.query.filter_by(usuario_id=usuario.id).all()
    jogos = BolaoJogo.query.filter_by(usuario_id=usuario.id).all()
    # bolões abertos para envio manual
    bolaos_abertos = Bolao.query.filter_by(status='aberto').all()
    # montar resumos por bolão que o usuário participa (convite aceito)
    import json
    participacoes = []
    for c in convites:
        b = Bolao.query.get(c.bolao_id)
        if not b:
            continue
        participantes = ConviteBolao.query.filter_by(bolao_id=b.id, status='aceito').count()
        # somatórios por faixa e valor total
        total_por_faixa = {}
        soma_por_faixa = {}
        jogos_b = BolaoJogo.query.filter_by(bolao_id=b.id).all()
        for j in jogos_b:
            if j.pontos is None:
                continue
            key = str(j.pontos)
            total_por_faixa[key] = total_por_faixa.get(key, 0) + 1
            soma_por_faixa[key] = soma_por_faixa.get(key, 0.0) + (j.premio_calculado or 0.0)
        # valor por participante
        por_participante = {}
        if participantes > 0:
            for k, v in soma_por_faixa.items():
                por_participante[k] = v / participantes
        participacoes.append({
            'bolao': b,
            'participantes': participantes,
            'total_por_faixa': total_por_faixa,
            'soma_por_faixa': soma_por_faixa,
            'por_participante': por_participante,
            'convite': c
        })
    return render_template('bolao.html', convites=convites, jogos=jogos, bolaos=bolaos_abertos, participacoes=participacoes)

# Aceitar convite
@app.route('/bolao/<int:bolao_id>/aceitar', methods=['POST'])
def aceitar_convite(bolao_id):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    conv = ConviteBolao.query.filter_by(bolao_id=bolao_id, usuario_id=usuario.id).first()
    if conv:
        conv.status = 'aceito'
        db.session.commit()
    return redirect(url_for('pagina_bolao'))

# Enviar jogo do histórico para um bolão
@app.route('/enviar_para_bolao/<int:predicao_id>', methods=['POST'])
def enviar_para_bolao(predicao_id):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    bolao_id = int(request.form.get('bolao_id'))
    import json
    # verificar se bolão está aberto
    bolao = Bolao.query.get_or_404(bolao_id)
    if bolao.status != 'aberto':
        flash('Bolão fechado. Não é possível enviar jogos.', 'info')
        return redirect(url_for('historico')) if predicao_id != 0 else redirect(url_for('pagina_bolao'))
    # verificar limite de jogos por convite aceito
    convite = ConviteBolao.query.filter_by(bolao_id=bolao_id, usuario_id=usuario.id, status='aceito').first()
    if not convite:
        flash('Você precisa aceitar o convite do bolão para enviar jogos.', 'info')
        return redirect(url_for('historico')) if predicao_id != 0 else redirect(url_for('pagina_bolao'))
    enviados = BolaoJogo.query.filter_by(bolao_id=bolao_id, usuario_id=usuario.id).count()
    if enviados >= (convite.jogos_permitidos or 0):
        flash('Limite de jogos atingido para este bolão.', 'info')
        return redirect(url_for('historico')) if predicao_id != 0 else redirect(url_for('pagina_bolao'))
    nums = None
    if predicao_id != 0:
        pred = Predicao.query.filter_by(id=predicao_id, usuario_id=usuario.id).first_or_404()
        # obter lista de números da predição
        try:
            if pred.numeros_json:
                nums = json.loads(pred.numeros_json)
        except Exception:
            nums = None
        if not nums:
            try:
                from ast import literal_eval
                nums = literal_eval(pred.numeros)
                if not isinstance(nums, (list, tuple)):
                    nums = [int(x) for x in str(pred.numeros).strip('[]').split(',') if x.strip()]
            except Exception:
                nums = []
        nums = [int(x) for x in nums]
        bj = BolaoJogo(bolao_id=bolao_id, usuario_id=usuario.id, numeros_json=json.dumps(nums), origem_predicao_id=pred.id)
        db.session.add(bj)
        pred.enviado = True
        db.session.commit()
        flash('Jogo enviado ao bolão com sucesso.', 'success')
        return redirect(url_for('historico'))
    else:
        # envio manual a partir da página Bolão
        # coletar dos 25 checkboxes
        nums = []
        for i in range(1, 26):
            if request.form.get(f'num_{i}'):
                nums.append(i)
        if len(set(nums)) == 15 and all(1 <= n <= 25 for n in nums):
            bj = BolaoJogo(bolao_id=bolao_id, usuario_id=usuario.id, numeros_json=json.dumps(nums))
            db.session.add(bj)
            db.session.commit()
            flash('Jogo enviado ao bolão com sucesso.', 'success')
        else:
            flash('Selecione exatamente 15 números válidos (1..25).', 'info')
        return redirect(url_for('pagina_bolao'))
    import json
    # obter lista de números da predição
    nums = None
    try:
        if pred.numeros_json:
            nums = json.loads(pred.numeros_json)
    except Exception:
        nums = None
    if not nums:
        try:
            from ast import literal_eval
            nums = literal_eval(pred.numeros)
            if not isinstance(nums, (list, tuple)):
                nums = [int(x) for x in str(pred.numeros).strip('[]').split(',') if x.strip()]
        except Exception:
            nums = []
    nums = [int(x) for x in nums]
    bj = BolaoJogo(bolao_id=bolao_id, usuario_id=usuario.id, numeros_json=json.dumps(nums), origem_predicao_id=pred.id)
    db.session.add(bj)
    pred.enviado = True
    db.session.commit()
    return redirect(url_for('historico'))

@app.route('/excluir/<int:id>', methods=['POST'])
@admin_required
def excluir(id):
    usuario = Usuario.query.get(id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
        try:
            compute_stats.cache_clear()
        except Exception:
            pass
    return redirect(url_for('painel_admin'))




@app.route('/admin/dashboard')
def admin_dashboard():
    total_usuarios = Usuario.query.count()
    total_predicoes = Predicao.query.count()
    total_admins = Usuario.query.filter_by(tipo='admin').count()
    # choose data source: 'predicoes' (saved predictions) or 'concursos' (official historical contests)
    source = request.args.get('source', 'predicoes')
    use_concursos = (source == 'concursos')
    # Analysis: prime counts per game, even/odd distribution, and sum ranges
    predicoes = []
    # if requested, try to read official historical contests from historico.xlsx
    if use_concursos:
        try:
            import pandas as pd
            hist_path = os.path.join(os.path.dirname(__file__), 'historico.xlsx')
            if os.path.exists(hist_path):
                df = pd.read_excel(hist_path, header=None)
                # build list of contest rows; each row should contain numeric entries (take first 15 ints)
                for _, row in df.iterrows():
                    vals = []
                    for v in row.tolist():
                        if pd.isna(v):
                            continue
                        try:
                            iv = int(v)
                            vals.append(iv)
                        except Exception:
                            # try to parse comma-separated strings
                            try:
                                parts = str(v).split(',')
                                for p in parts:
                                    p = p.strip()
                                    if p:
                                        vals.append(int(p))
                            except Exception:
                                pass
                        if len(vals) >= 15:
                            first15 = [int(x) for x in vals[:15]]
                            # validate numbers are in 1..25
                            valid = all(1 <= n <= 25 for n in first15)
                            if valid:
                                # create a lightweight object similar to Predicao for reuse of parsing logic
                                class _P: pass
                                p = _P()
                                p.numeros = str(first15)
                                predicoes.append(p)
        except Exception as e:
            print('Erro ao carregar historico.xlsx:', e)
            use_concursos = False

    if not use_concursos:
        predicoes = Predicao.query.all()
    primes = set([2,3,5,7,11,13,17,19,23])  # primes within 1-25
    prime_count_hist = {}
    prime_number_freq = {}
    even_count_hist = {}
    sum_values = []
    for p in predicoes:
        nums = []
        # preferir JSON se disponível
        try:
            if getattr(p, 'numeros_json', None):
                import json
                nums = json.loads(p.numeros_json)
            else:
                raise Exception('no json')
        except Exception:
            try:
                nums = ast.literal_eval(p.numeros)
                # if stored as string with commas but not list, attempt split
                if not isinstance(nums, (list, tuple)):
                    nums = [int(x) for x in str(p.numeros).strip('[]').split(',') if x.strip()]
            except Exception:
                try:
                    nums = [int(x) for x in str(p.numeros).strip('[]').split(',') if x.strip()]
                except Exception:
                    nums = []
        # normalize and validate: must be exactly 15 integers in 1..25
        try:
            nums = [int(x) for x in nums]
        except Exception:
            continue
        # filter invalid values
        nums = [n for n in nums if isinstance(n, int) and 1 <= n <= 25]
        if len(nums) != 15:
            # skip malformed or aggregated rows to avoid huge sums
            continue
        prime_count = sum(1 for n in nums if n in primes)
        # build prime number frequency
        for n in nums:
            if n in primes:
                prime_number_freq[n] = prime_number_freq.get(n, 0) + 1
        even_count = sum(1 for n in nums if n % 2 == 0)
        s = sum(nums)
        sum_values.append(s)
        prime_count_hist[prime_count] = prime_count_hist.get(prime_count, 0) + 1
        even_count_hist[even_count] = even_count_hist.get(even_count, 0) + 1

    # Determine most common prime count(s)
    most_common_primes = []
    if prime_count_hist:
        max_freq = max(prime_count_hist.values())
        most_common_primes = sorted([(cnt, freq) for cnt, freq in prime_count_hist.items() if freq == max_freq], key=lambda x: -x[1])

    # Prime numbers frequency list (sorted desc)
    prime_number_list = sorted([{'prime': p, 'count': c} for p, c in prime_number_freq.items()], key=lambda x: x['count'], reverse=True)

    # Determine most common even count(s) and corresponding odd counts
    most_common_evens = []
    most_common_odds = []
    even_count_list = []
    odd_count_list = []
    if even_count_hist:
        # even histogram list (convert to list of dicts)
        even_count_list = [{'pares': cnt, 'vezes': freq} for cnt, freq in even_count_hist.items()]
        # compute odd histogram from even counts
        odd_hist = {15 - cnt: freq for cnt, freq in even_count_hist.items()}
        odd_count_list = [{'impares': cnt, 'vezes': freq} for cnt, freq in odd_hist.items()]
        # determine max frequencies to scale bars
        # sort lists by frequency descending for display (most frequent first)
        even_count_list = sorted(even_count_list, key=lambda x: x['vezes'], reverse=True)
        odd_count_list = sorted(odd_count_list, key=lambda x: x['vezes'], reverse=True)
        # find most frequent
        max_freq_e = max(even_count_hist.values())
        most_common_evens = sorted([(cnt, freq) for cnt, freq in even_count_hist.items() if freq == max_freq_e], key=lambda x: -x[1])
        max_freq_o = max(odd_hist.values())
        most_common_odds = sorted([(cnt, freq) for cnt, freq in odd_hist.items() if freq == max_freq_o], key=lambda x: -x[1])

    # Use narrower fixed sum ranges (bin width = 10) for 15 numbers in 1..25 (15..375)
    # This mirrors compute_stats() and the index behavior so the dashboard shows
    # more granular and filled ranges. Also filter out empty bins before taking Top-10.
    sum_range_counts = []
    if sum_values:
        min_possible = 15
        max_possible = 375
        bin_width = 10
        bins = []
        start = min_possible
        while start <= max_possible:
            end = min(start + bin_width - 1, max_possible)
            bins.append((start, end))
            start = end + 1
        # count
        bin_counts = [0] * len(bins)
        for s in sum_values:
            s_clamped = max(min_possible, min(max_possible, s))
            idx = min((s_clamped - min_possible) // bin_width, len(bins) - 1)
            bin_counts[idx] += 1
        sum_range_counts = [({'range': f"{b[0]}-{b[1]}", 'count': bin_counts[i]}) for i, b in enumerate(bins)]
        # remove empty bins so Top-10 includes only filled ranges
        sum_range_counts = [r for r in sum_range_counts if r['count'] > 0]
        sum_range_counts = sorted(sum_range_counts, key=lambda x: x['count'], reverse=True)[:10]

    # debug: print computed top sum ranges so we can verify server-side what is being passed to the template
    try:
        print(f"[DEBUG admin_dashboard] data_source={'concursos' if use_concursos else 'predicoes'} sum_range_counts={sum_range_counts}")
        print(f"[DEBUG admin_dashboard] even_count_list={even_count_list} odd_count_list={odd_count_list}")
        print(f"[DEBUG admin_dashboard] even_max_vezes={even_max_vezes} odd_max_vezes={odd_max_vezes}")
    except Exception:
        pass
    # convert most_common_primes/evens from [(count, freq), ...] to [count, ...] for client
    mcp = [cnt for cnt, _ in most_common_primes]
    mce = [cnt for cnt, _ in most_common_evens]
    # compute max frequencies for even/odd histograms (used to scale bars)
    even_max_vezes = max([it['vezes'] for it in even_count_list]) if even_count_list else 0
    odd_max_vezes = max([it['vezes'] for it in odd_count_list]) if odd_count_list else 0
    # pre-compute percentage width for bars to avoid template math mistakes
    if even_max_vezes:
        for it in even_count_list:
            it['pct'] = round((it['vezes'] / even_max_vezes) * 100, 1)
    if odd_max_vezes:
        for it in odd_count_list:
            it['pct'] = round((it['vezes'] / odd_max_vezes) * 100, 1)

    # create display lists ordered by number of pares/impares (ascending) so the UI shows 0..15 progression
    even_display_list = sorted(even_count_list, key=lambda x: x['pares']) if even_count_list else []
    odd_display_list = sorted(odd_count_list, key=lambda x: x['impares']) if odd_count_list else []
    return render_template('dashboard.html', total_usuarios=total_usuarios, total_predicoes=total_predicoes, total_admins=total_admins,
                           most_common_primes=mcp, prime_number_list=prime_number_list,
                           most_common_evens=mce, most_common_odds=most_common_odds,
                           even_count_list=even_count_list, odd_count_list=odd_count_list, sum_range_counts=sum_range_counts,
                           even_max_vezes=even_max_vezes, odd_max_vezes=odd_max_vezes,
                           even_display_list=even_display_list, odd_display_list=odd_display_list,
                           data_source = 'concursos' if use_concursos else 'predicoes')


@app.route('/alterar_senha', methods=['GET', 'POST'])
def alterar_senha():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.filter_by(nome=session['usuario']).first()
    if request.method == 'POST':
        senha_atual = request.form['senha_atual']
        nova_senha = request.form['nova_senha']
        if not check_password_hash(usuario.senha, senha_atual):
            return render_template('perfil.html', usuario=usuario, erro="Senha atual incorreta.")
        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()
        return render_template('perfil.html', usuario=usuario, mensagem="Senha alterada com sucesso.")
    return render_template('perfil.html', usuario=usuario)
@app.route('/sugestao_automatica')
def sugestao_automatica():
    import random
    sugestao = random.sample(range(1, 26), 15)
    return {"numeros": sugestao}

if __name__ == '__main__':
    app.run(debug=True)
