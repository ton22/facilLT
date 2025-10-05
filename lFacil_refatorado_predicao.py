import numpy as np
import joblib
from tensorflow.keras.models import load_model

NUM_RANGE = range(1, 26)

def carregar_modelos():
    modelo_nn = load_model("modelo_numeros.keras")
    modelo_rf = joblib.load("modelo_pontuacao.pkl")
    return modelo_nn, modelo_rf

# cache models to avoid reloading on every call
_MODELOS_CACHE = {"nn": None, "rf": None}

def _get_modelos():
    if _MODELOS_CACHE["nn"] is None or _MODELOS_CACHE["rf"] is None:
        nn, rf = carregar_modelos()
        _MODELOS_CACHE["nn"] = nn
        _MODELOS_CACHE["rf"] = rf
    return _MODELOS_CACHE["nn"], _MODELOS_CACHE["rf"]

def preparar_entrada(lista_numeros):
    entrada = np.array([int(i in lista_numeros) for i in NUM_RANGE]).reshape(1, -1)
    return entrada

def predizer(lista_numeros):
    modelo_nn, modelo_rf = _get_modelos()
    entrada = preparar_entrada(lista_numeros)
    
    predicao = modelo_nn.predict(entrada, verbose=0)[0]
    numeros_previstos = sorted(NUM_RANGE, key=lambda j: predicao[j-1], reverse=True)[:15]
    pontuacao = modelo_rf.predict([predicao])[0]
    
    return {
        "numeros": numeros_previstos,
        "pontuacao": round(pontuacao, 1)
    }


def avaliar(lista_numeros):
    """Avalia (pontua) o jogo fornecido sem alterar os números.
    Retorna a pontuação estimada (float arredondado)."""
    modelo_nn, modelo_rf = _get_modelos()
    entrada = preparar_entrada(lista_numeros)
    predicao = modelo_nn.predict(entrada, verbose=0)[0]
    pontuacao = modelo_rf.predict([predicao])[0]
    return round(pontuacao, 1)
