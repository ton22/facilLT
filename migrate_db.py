import sqlite3
from datetime import datetime

# Conectar ao banco de dados
conn = sqlite3.connect('instance/lotofacil.db')
cursor = conn.cursor()

# Verificar se as colunas já existem
cursor.execute("PRAGMA table_info(usuario)")
columns = [column[1] for column in cursor.fetchall()]

# Adicionar coluna data_criacao se não existir
if 'data_criacao' not in columns:
    print("Adicionando coluna data_criacao à tabela usuario...")
    cursor.execute("ALTER TABLE usuario ADD COLUMN data_criacao TIMESTAMP")
    # Definir valor padrão para registros existentes
    current_time = datetime.utcnow().isoformat()
    cursor.execute(f"UPDATE usuario SET data_criacao = '{current_time}'")

# Adicionar coluna ultimo_acesso se não existir
if 'ultimo_acesso' not in columns:
    print("Adicionando coluna ultimo_acesso à tabela usuario...")
    cursor.execute("ALTER TABLE usuario ADD COLUMN ultimo_acesso TIMESTAMP")

# Salvar alterações
conn.commit()
print("Migração concluída com sucesso!")

# Fechar conexão
conn.close()