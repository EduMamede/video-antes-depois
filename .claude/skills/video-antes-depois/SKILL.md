---
name: video-antes-depois
description: Monta um vídeo vertical de antes e depois de um tratamento (clínica de estética, emagrecimento, dermatologia, capilar, odontologia), com o resultado guardado em segredo até a revelação. Gera a versão para mandar à própria paciente no WhatsApp ou a versão pública para o Instagram. Usar quando pedirem "vídeo de antes e depois", "vídeo de resultado da paciente", "mostrar a evolução", "fechamento do tratamento" ou /video-antes-depois.
---

# /video-antes-depois

Transforma as fotos de antes e depois de um caso num vídeo vertical (1080x1920) de 30 a 45 segundos:
abertura com a marca da clínica → cada vista com o DEPOIS escondido até a revelação → números (opcional) → fechamento.

Fale sempre em português, de forma simples: quem usa é o dono da clínica ou a equipe, não um programador.

## Regras que nunca mudam
1. **Fotos sem alteração.** Nada de filtro, brilho, retoque, recorte ou "melhorar" a imagem. O script copia o arquivo como está.
   A única conversão permitida é de formato (HEIC do iPhone para JPG), sem mexer na imagem.
2. **Sem dado da paciente.** Nada de nome, rosto identificável, medicamento ou preço no vídeo. Se a foto mostrar o rosto,
   avise e peça uma foto sem o rosto. Prints de exame (bioimpedância etc.) nunca entram no vídeo: só os números são redesenhados.
3. **Versão pública só com autorização.** Pergunte se a paciente autorizou o uso das imagens. Sem um "sim" claro,
   gere só a versão para a paciente. O script também bloqueia (`"autorizacao_paciente": true` no config).
4. **Sem promessa.** Nada de "resultado garantido", "em X dias você também". A versão pública já sai com
   "Resultados podem variar de pessoa para pessoa." e "Imagens publicadas com autorização da paciente."
5. **Números só os reais.** Nunca invente nem arredonde para "ficar bonito". Confira a conta das diferenças.
6. **Área médica:** lembre que publicidade médica segue a Resolução CFM 2.336/2023 (antes e depois permitido com
   autorização, sem edição e sem promessa). Outras profissões seguem o próprio conselho. Na dúvida, o dono confere.

## Passo a passo

### 1. Perguntar (uma mensagem só)
- Para quem é o vídeo: **paciente** (WhatsApp, parabéns no final) ou **público** (Instagram, chamada para agendar)? Pode ser os dois.
- Onde estão as fotos? Cada vista pode ser **uma foto já montada** (antes e depois lado a lado) ou **duas fotos separadas**. De 1 a 4 vistas.
- Tem números para mostrar (peso, medidas, bioimpedância)? Datas de início e fim?
- Site ou Instagram da clínica (para tirar as cores, as fontes e a logo), nome do responsável técnico com CRM/RQE ou registro.
- A paciente autorizou o uso das imagens? (só para a versão pública)

### 2. Organizar a pasta do caso
Crie `casos/<nome-do-caso>/` (nunca use o nome da paciente no nome da pasta; use "caso-01") com:
- `fotos/` com as fotos originais (copie, não mova).
- `marca/` com a logo em versão **clara** (para fundo escuro, PNG transparente) e, se houver, o símbolo da marca.
- `fontes/` (opcional) com as fontes da clínica em .ttf. Sem elas, o vídeo usa Cormorant Garamond e Jost.
- `config.json` (ver o modelo em `exemplo/config.json`).

Identidade visual: abra o site da clínica e tire 3 cores (`escuro` para o fundo, `destaque` para os detalhes e
`claro` para a tela dos números) e, se der, a logo. Se a logo só existir em cor escura, avise o dono e peça a versão branca.

### 3. Preencher o config.json
Copie `exemplo/config.json` e troque tudo. Campos principais:
- `clinica`: `nome`, `assinatura` (rodapé, ex.: "Dra. Fulana · Dermatologista · CRM-SP 00000 · RQE 00000"),
  `nome_linha`, `logo_clara`, `simbolo` (opcional), `instagram`.
- `visual`: `escuro`, `destaque`, `claro` (obrigatórias); `destaque_texto` se o destaque ficar fraco no fundo claro; fontes opcionais.
- `autorizacao_paciente`: `true` só com o "sim" da paciente.
- `caso.metodo` (nome do tratamento ou programa), `caso.abertura` (2 linhas; `<em>palavra</em>` fica em itálico e na cor de destaque).
- `caso.vistas`: `{"titulo": "De <em>frente</em>", "foto": "fotos/x.jpg"}` ou `{"titulo": ..., "antes": ..., "depois": ...}`.
- `caso.numeros` (opcional): `rotulo`, `linhas` = `[rótulo, antes, depois, unidade, diferença]` (até 4), `fecho` e `fecho_paciente` (2 linhas).
- `caso.final_paciente`: `periodo`, `agradecimento`, `assina`. `caso.final_publico`: `frase`, `botao`, `linha` (cidade/atendimento).
- `musica` (opcional): sem o campo, o vídeo usa a música que vem com a ferramenta (Sascha Ende, CC BY 4.0), já com as
  cenas no ritmo dela. `false` tira a música; um caminho troca por outra (só uma que a clínica tenha direito de usar).

### 4. Gerar e renderizar
Na pasta da ferramenta:
```
python motor/gerar.py casos/<caso>/config.json paciente
cd casos/<caso>/saida/paciente/composition
npx hyperframes check
npx hyperframes render --quality high --output ../video.mp4
```
(troque `paciente` por `publico` para a outra versão). Na primeira vez, rode `npm install` na pasta da ferramenta.

### 5. Conferir antes de entregar
Tire quadros do vídeo (`ffmpeg -i video.mp4 -vf "fps=1/3,scale=270:-1,tile=6x2" -frames:v 1 quadros.png`) e olhe:
o DEPOIS não aparece antes da revelação, os textos não passam da tela, os números batem com o exame, sem nome nem rosto.

### 6. Entregar
- Versão **paciente**: escreva também a mensagem de WhatsApp (oi, [nome], fim do tratamento, 1 número principal, parabéns, assinatura).
  O nome entra só na mensagem, nunca no vídeo.
- Versão **pública**: escreva a legenda do post com o aviso "Resultados podem variar", sem promessa e, se usou a
  música padrão, com o crédito "Música: Sascha Ende (ende.app), CC BY 4.0".
- Diga onde ficou o `video.mp4` e como refazer se quiserem mudar algum texto (editar o config e rodar o passo 4 de novo).
