#!/usr/bin/env python3
"""
Script para debugar o histórico de predições
Verifica quantas predições estão salvas no banco para cada usuário
"""

from app import app
from models import db, Usuario, Predicao

def debug_historico():
    with app.app_context():
        print("=== DEBUG HISTÓRICO DE PREDIÇÕES ===\n")
        
        # Listar todos os usuários
        usuarios = Usuario.query.all()
        print(f"Total de usuários: {len(usuarios)}")
        
        for usuario in usuarios:
            print(f"\nUsuário: {usuario.nome} (ID: {usuario.id})")
            print(f"Tipo: {usuario.tipo}")
            print(f"Aprovado: {usuario.aprovado}")
            
            # Contar predições do usuário
            total_predicoes = Predicao.query.filter_by(usuario_id=usuario.id).count()
            print(f"Total de predições: {total_predicoes}")
            
            # Mostrar as últimas 5 predições
            predicoes = Predicao.query.filter_by(usuario_id=usuario.id).order_by(
                Predicao.id.desc()).limit(5).all()
            
            if predicoes:
                print("Últimas 5 predições:")
                for p in predicoes:
                    print(f"  ID: {p.id}, Data: {p.data}, Números: {p.numeros}, Pontuação: {p.pontuacao}")
            else:
                print("  Nenhuma predição encontrada")
        
        # Verificar total geral de predições
        total_geral = Predicao.query.count()
        print(f"\n=== TOTAL GERAL DE PREDIÇÕES: {total_geral} ===")
        
        # Mostrar todas as predições (limitado a 20 para não sobrecarregar)
        todas_predicoes = Predicao.query.order_by(Predicao.id.desc()).limit(20).all()
        print(f"\nÚltimas 20 predições no sistema:")
        for p in todas_predicoes:
            usuario_nome = Usuario.query.get(p.usuario_id).nome if Usuario.query.get(p.usuario_id) else "Usuário não encontrado"
            print(f"  ID: {p.id}, Usuário: {usuario_nome}, Data: {p.data}, Números: {p.numeros}")

if __name__ == "__main__":
    debug_historico()