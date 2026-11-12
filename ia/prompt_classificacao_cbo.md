# Prompt — classificação de CBOs em macrofamílias ocupacionais

Este é o prompt **exato** enviado ao LLM, lote a lote (≈440 CBOs por lote, 5 lotes,
2.207 CBOs no total). No lugar de `{LISTA}` entra o lote, uma ocupação por linha no
formato `código | título`.

---

Você é um especialista em mercado de trabalho industrial brasileiro e na Classificação
Brasileira de Ocupações (CBO 2002). Uma consultoria está analisando o Novo CAGED de
Santa Catarina para responder: *quais regiões e setores industriais enfrentam apagão de
mão de obra ou expansão acelerada, e como renda e escolaridade explicam esses gargalos?*

Classifique **cada** ocupação abaixo em **exatamente uma** macrofamília, usando
**somente** os códigos desta tabela:

| Código | Macrofamília | Inclui |
|---|---|---|
| OP_METAL | Operacional – Metalmecânica e eletroeletrônica | soldadores, torneiros, caldeireiros, operadores de usinagem/CNC, montadores de máquinas, veículos e equipamentos, montadores eletroeletrônicos, fundição, siderurgia |
| OP_TEXTIL | Operacional – Têxtil, confecção e calçados | fiação, tecelagem, costura, corte, acabamento, tinturaria, calçados, couro |
| OP_ALIM | Operacional – Alimentos, bebidas e agroindústria | abate e processamento de carnes, laticínios, panificação industrial, bebidas, fumo |
| OP_OUTRAS | Operacional – Outras indústrias de transformação e extrativa | madeira e móveis, papel, gráfica, plástico e borracha, química, cerâmica, vidro, mineração, alimentadores de linha e operadores de produção não específicos |
| CONSTR | Construção civil e infraestrutura | pedreiros, serventes de obra, carpinteiros de obra, armadores, pintores de obra, operadores de máquinas pesadas de obra |
| MANUT | Manutenção, reparação e instalação | mecânicos de manutenção, eletricistas de manutenção/instalação, reparadores, instaladores |
| LOGIST | Logística, transporte e armazenagem | motoristas, operadores de empilhadeira, almoxarifes, estoquistas, carregadores, conferentes |
| TEC_IND | Técnicos industriais, de TI e de qualidade (nível médio) | técnicos em mecânica, eletrônica, automação, química, segurança do trabalho, qualidade, desenhistas técnicos, técnicos de TI e suporte |
| ENG_TI | Engenharia, TI e ciências (nível superior) | engenheiros, analistas e desenvolvedores de sistemas, cientistas, químicos, físicos, estatísticos |
| GESTAO | Gestão, supervisão e liderança | diretores, gerentes, supervisores, encarregados e chefes (de qualquer área) |
| ADM | Administrativo e escritório | auxiliares/assistentes administrativos, recepcionistas, contabilidade, RH, finanças, profissionais de nível superior de áreas administrativas/jurídicas |
| COMERCIO | Comércio, vendas e atendimento | vendedores, operadores de caixa, repositores, representantes comerciais, operadores de telemarketing |
| SERV | Serviços (saúde, educação, alimentação, limpeza, segurança e outros) | profissionais de saúde e educação, cozinheiros, garçons, faxineiros, vigilantes, porteiros, cabeleireiros, cuidadores, forças armadas e policiais |
| AGRO | Agropecuária, pesca e florestal | trabalhadores agrícolas e da pecuária, avicultura, suinocultura, pesca, silvicultura, operadores de máquinas agrícolas |

Regras:
1. A macrofamília descreve **a ocupação**, não o setor da empresa (um vendedor numa
   indústria continua sendo COMERCIO).
2. Supervisores, encarregados e chefes vão para GESTAO, mesmo na produção.
3. Técnicos de nível médio de áreas não industriais (ex.: técnico de enfermagem) vão
   para SERV ou ADM, conforme a área; TEC_IND é só para técnicos industriais/TI/qualidade.
4. Para cada ocupação, informe também:
   - `nivel`: `OPERACIONAL`, `TECNICO` (nível médio/técnico), `SUPERIOR` ou `GESTAO`;
   - `industrial`: `S` se a ocupação é tipicamente exercida na indústria (transformação,
     extrativa, construção, energia/utilidades) ou na sua manutenção/logística interna;
     `N` caso contrário.
5. Se o título vier como `[sem título no dicionário]`, use a família CBO (4 primeiros
   dígitos) e os títulos irmãos informados para inferir a classificação. O código
   `999999` (não informado) recebe `macrofamilia=NAO_CLASSIFICADO`, `nivel=NA`,
   `industrial=N`.

Responda **somente** com CSV separado por `;`, com cabeçalho e **uma linha por
ocupação, na mesma ordem e com o mesmo código** da lista (não omita nenhuma, não
repita o título):

```
cbo;macrofamilia;nivel;industrial
```

Lista de ocupações:

{LISTA}
