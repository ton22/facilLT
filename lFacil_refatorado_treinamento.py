import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib

ARQUIVO_EXCEL = "historico.xlsx"
PLANILHA = "historico"
NUMEROS_SORTEADOS = [f"Numero {i}" for i in range(1, 16)]
NUM_RANGE = range(1, 26)

def carregar_dados():
    df = pd.read_excel(ARQUIVO_EXCEL, sheet_name=PLANILHA)
    for i in NUM_RANGE:
        df[f"N{i}"] = df[NUMEROS_SORTEADOS].apply(lambda row: int(i in row.values), axis=1)
    return df

def treinar_rede_neural(X, y):
    modelo = Sequential([
        Input(shape=(25,)),
        Dense(128, activation='relu'),
        Dense(64, activation='relu'),
        Dense(25, activation='sigmoid')
    ])
    modelo.compile(optimizer='adam', loss='binary_crossentropy')
    modelo.fit(X, y, epochs=100, batch_size=32, verbose=0)
    return modelo

def calcular_acertos(previstos, reais):
    return len(set(previstos) & set(reais))

def treinar_modelo_auxiliar(X_rf, y_rf):
    X_train, X_test, y_train, y_test = train_test_split(X_rf, y_rf, test_size=0.2, random_state=42)
    modelo_rf = RandomForestRegressor()
    modelo_rf.fit(X_train, y_train)
    erro = mean_squared_error(y_test, modelo_rf.predict(X_test))
    return modelo_rf, erro

def salvar_modelos(modelo_nn, modelo_rf):
    modelo_nn.save("modelo_numeros.keras")
    joblib.dump(modelo_rf, "modelo_pontuacao.pkl")

def treinar_modelos(df):
    X_nn = df[[f"N{i}" for i in NUM_RANGE]].iloc[:-1].values
    y_nn = df[[f"N{i}" for i in NUM_RANGE]].iloc[1:].values

    modelo_nn = treinar_rede_neural(X_nn, y_nn)

    entradas_rf = []
    pontuacoes = []

    for i in range(len(X_nn)):
        entrada = X_nn[i].reshape(1, -1)
        predicao = modelo_nn.predict(entrada, verbose=0)[0]
        numeros_previstos = sorted(NUM_RANGE, key=lambda j: predicao[j-1], reverse=True)[:15]
        reais = [j for j in NUM_RANGE if y_nn[i][j-1] == 1]
        acertos = calcular_acertos(numeros_previstos, reais)
        entradas_rf.append(predicao)
        pontuacoes.append(acertos)

    modelo_rf, erro = treinar_modelo_auxiliar(np.array(entradas_rf), np.array(pontuacoes))
    salvar_modelos(modelo_nn, modelo_rf)

    return modelo_nn, modelo_rf, erro

def executar_treinamento():
    df = carregar_dados()
    _, _, erro = treinar_modelos(df)
    return f"Treinamento concluído com erro médio de {erro:.2f}"
