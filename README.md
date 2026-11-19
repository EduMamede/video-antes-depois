# Vídeo de antes e depois para clínicas

Uma skill do Claude que transforma as fotos de antes e depois de um tratamento num vídeo vertical, pronto para:

- **mandar para a própria paciente no WhatsApp**, fechando o tratamento ("Parabéns pela sua jornada"), ou
- **postar no Instagram**, com chamada para agendar e os avisos obrigatórios.

O resultado fica escondido até a revelação, foto por foto. As fotos entram **exatamente como foram tiradas**: sem filtro, sem retoque, sem recorte.
O vídeo já sai com música e com as cenas no ritmo dela (créditos em [CREDITOS.md](CREDITOS.md)).

| Para a paciente | Para o Instagram |
|---|---|
| [exemplo/saida/paciente/video.mp4](exemplo/saida/paciente/video.mp4) | [exemplo/saida/publico/video.mp4](exemplo/saida/publico/video.mp4) |

*(o exemplo usa ilustrações e números inventados)*

## Por que mandar o vídeo para a paciente
Quem vê o próprio resultado volta e fala de você. É o "Mostra" do método **Fala, Faz, Mostra**:
fala com verdade, faz o que prometeu e mostra o resultado.

## O que você precisa
1. **Claude Code** (o Claude no computador), com uma assinatura do Claude: https://claude.com/claude-code
2. **Node.js** (gratuito): https://nodejs.org (baixe a versão "LTS" e instale clicando em "Avançar").
3. **Python** (gratuito): https://www.python.org/downloads (no Windows, marque "Add Python to PATH" na instalação).

## Como usar (passo a passo)
1. Clique em **Code → Download ZIP** nesta página e descompacte numa pasta do seu computador.
2. Abra o Claude Code **nessa pasta**.
3. Na primeira vez, peça: *"instala as dependências"* (ele roda `npm install` e `pip install pillow`).
4. Peça: **/video-antes-depois** e responda às perguntas. Ele pede as fotos, os números (se tiver), o site da clínica e se a paciente autorizou.
5. O vídeo sai em `casos/<seu-caso>/saida/<versão>/video.mp4`.

As fotos dos seus casos ficam só no seu computador, na pasta `casos/`.

## Regras que a skill segue
- Foto sem nenhuma alteração.
- Sem nome, rosto, medicamento ou preço no vídeo.
- Versão pública só com a autorização da paciente, com "Resultados podem variar de pessoa para pessoa."
- Na área médica, publicidade segue a Resolução CFM 2.336/2023. Outras profissões seguem o próprio conselho. Confira a regra do seu.

## Uso
Livre para usar e adaptar na sua clínica (licença MIT). Créditos e licenças das fontes e sons em `CREDITOS.md`.

Feito por Eduardo Mamede · Instagram [@fidemx.app](https://www.instagram.com/fidemx.app/)
