# Usamos uma imagem base oficial do Python
FROM python:3.9-slim

# Definimos o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiamos o arquivo de requisitos para o contêiner
COPY requirements.txt .

# Instalamos as bibliotecas
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos o resto dos arquivos do seu projeto para o contêiner
COPY . .

# Expomos a porta que o Streamlit usa e damos o comando para iniciar a aplicação
EXPOSE 8501
CMD ["streamlit", "run", "app_sql_agent.py"]