-- Remove a tabela se ela já existir, para garantir um começo limpo
DROP TABLE IF EXISTS dados_mario;

-- Cria a tabela com as colunas corretas do seu arquivo
CREATE TABLE dados_mario (
    id SERIAL PRIMARY KEY,
    "ano" INTEGER,
    "mes" TEXT,
    "nome_receita" TEXT,
    "arrecadado" NUMERIC
);

-- Copia os dados do CSV para a tabela recém-criada
COPY dados_mario (
    "ano",
    "mes",
    "nome_receita",
    "arrecadado"
) FROM '/docker-entrypoint-initdb.d/base_mario_agrupado_30julho_manha_fim.csv' DELIMITER ',' CSV HEADER;