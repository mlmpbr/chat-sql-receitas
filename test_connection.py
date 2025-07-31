import sqlalchemy

# A URL de conexão usando o nome de host especial do Docker.
db_url = "postgresql+psycopg2://user:password@host.docker.internal:5432/meubanco"

print("Tentando conectar ao banco de dados em:", db_url)

try:
    engine = sqlalchemy.create_engine(db_url)
    with engine.connect() as connection:
        print("\n" + "="*50)
        print(">>> SUCESSO! A CONEXÃO FOI ESTABELECIDA! <<<")
        print("="*50 + "\n")
except Exception as e:
    print("\n" + "X"*50)
    print(">>> FALHA! A CONEXÃO NÃO FOI ESTABELECIDA. <<<")
    print("X"*50 + "\n")
    print("Detalhes do erro:", e)