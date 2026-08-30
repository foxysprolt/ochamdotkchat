let botao = document.querySelector(".botao-ajuda");
let input = document.querySelector(".caixa-texto");
let chat = document.querySelector("#chat");

let urlServidor = "https://chat-ochamado-549878631100.southamerica-east1.run.app";

// Histórico inicia limpo sem mensagens prévias
let historico = [];

// Chat inicia limpo ao carregar a página
window.onload = () => {};

// FUNÇÃO PARA IDENTIFICAR LINKS E TORNÁ-LOS CLICÁVEIS
function formatarLinks(texto) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return texto.replace(urlRegex, function(url) {
        return `<a href="${url}" target="_blank" class="link-chat">${url}</a>`;
    });
}

function adicionarMensagem(texto, tipo) {
    let div = document.createElement("div");
    div.classList.add("msg", tipo);
    
    let textoFormatado = formatarLinks(texto);
    div.innerHTML = textoFormatado.replace(/\n/g, "<br>");
    
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

async function enviarMensagem() {
    let texto = input.value.trim();
    if (!texto) return;

    adicionarMensagem(texto, "user");
    historico.push({ role: "user", content: texto }); 
    
    input.value = "";
    adicionarMensagem("PowerBot: analisando...", "bot");

    try {
        const response = await fetch(urlServidor, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ historico: historico }) 
        });

        if (!response.ok) {
            const erroCorpo = await response.json();
            throw new Error(erroCorpo.erro || "Erro desconhecido");
        }

        let dados = await response.json();
        
        if (chat.lastChild) chat.lastChild.remove();

        let resultado = dados.resposta; 
        adicionarMensagem(resultado, "bot");
        historico.push({ role: "assistant", content: resultado });

    } catch (erro) {
        if (chat.lastChild) chat.lastChild.remove();
        adicionarMensagem("Erro: " + erro.message, "bot");
        console.error("Erro detalhado:", erro);
    }
}

botao.addEventListener("click", enviarMensagem);

input.addEventListener("keydown", function(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        enviarMensagem();
    }
});
