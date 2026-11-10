# Entregáveis — Datathon CDIA 2026 (Raio-X do Mercado de Trabalho Industrial em SC)

Checklist consolidada a partir do **PowerPoint oficial** (`documentos_apoio/Datathon CDIA 2026 - UniSENAI.pptx`)
e do **Guia do Participante** (`documentos_apoio/Guia do Participante.docx`).

Tudo deve ser submetido em um **repositório Git público** (GitHub/GitLab/Bitbucket) e entregue
pelo **formulário oficial** (`https://bit.ly/4jBn07X`).

---

## ✅ Entregáveis obrigatórios (3 artefatos)

### 1. Script ou Notebook (`.ipynb` ou `.py`)
Código-fonte **documentado** com o pipeline completo:
- [ ] Carga das bases em **Python (Pandas/Polars)** + verificação de schema
- [ ] Tratamento de inconsistências e **filtragem das exclusões (MOV × EX)**
- [ ] **Merge/join** do CAGED com os dados municipais via **código do município**
- [ ] Métrica normalizada **"Saldo de Vagas por 10.000 habitantes"**
- [ ] **Enriquecimento com IA Generativa**: chamada de API / prompts que **agrupam 200+ CBOs em macrofamílias**
- [ ] Exportação final dos dados tratados

### 2. Dashboard / Painel Analítico (Python)
- [ ] Interativo, com **no mínimo 3 KPIs/indicadores-chave**
- [ ] **Power BI ou Streamlit**
- [ ] Representações adequadas: **mapa** (território), **barras** (setor) e **dispersão** (renda × escolaridade)
- [ ] Fluxo de storytelling: localizar o problema → entender a causa-raiz → ler a recomendação

### 3. Pitch Executivo (3 minutos)
- [ ] Apresentação de **slides** com a narrativa
- [ ] Diagnóstico final + gargalos + **recomendações práticas** para a indústria
- [ ] Rigorosamente dentro de **3 minutos**

---

## 🎯 Pergunta central de negócio
> "Quais regiões e setores industriais de SC enfrentam **apagão de mão de obra** ou
> **expansão acelerada**, e como **renda e escolaridade** explicam esses gargalos?"

Cobrir os **3 eixos de investigação**:
- **Territorial e setorial** — distribuição das movimentações no mapa / setores que lideram
- **Perfil socioeconômico** — perfil de admitidos × desligados, escolaridade e faixa salarial
- **Qualificação e IA** — agrupamento dos CBOs em macrofamílias (escassez operacional vs. técnica/engenharia)

---

## 📋 Regras do guia a respeitar
- **Equipe:** 5 integrantes — 2 da 4ª fase + 3 da 2ª fase; líder faz a inscrição no formulário
- **IA generativa** é permitida e **incentivada** em todas as etapas
- **Banca:** especialistas das empresas parceiras
- **Entrega:** exclusivamente pelo formulário oficial
- **Local/horário (ACATE):** 10/11 10:00–11:40 (montagem) · 13/11 08:30–09:50 (pitches) · 13/11 10:00–11:40 (apresentação)

---

## 🧭 Critérios de avaliação
1. Compreensão do problema e contexto industrial de SC
2. Embasamento analítico e diagnóstico (renda/escolaridade × gargalos; premissas e limites explícitos)
3. Dashboard e storytelling (KPIs em destaque, gráficos adequados)
4. Recomendações e valor de negócio (conectadas às macrofamílias de CBO geradas por IA)
5. Comunicação e pitch (clareza, tom executivo, 3 min)

---

## 📌 Status do repositório
- [x] `dataset/` completo (CAGED em Parquet + municípios + dicionário)
- [ ] Entregável 1 — Notebook/Script de pipeline
- [ ] Entregável 2 — Dashboard analítico
- [ ] Entregável 3 — Pitch (slides, 3 min)
