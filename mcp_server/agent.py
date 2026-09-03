import asyncio
import json
import os

import ollama

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# ============================================================
# CONFIGURATION
# ============================================================

MCP_URL = os.getenv(
    "MCP_URL",
    "http://127.0.0.1:8002/mcp",
)

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
)

MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:7b",
)


# Client Ollama
ollama_client = ollama.Client(host=OLLAMA_HOST)


# ============================================================
# CONVERSION DES TOOLS MCP → FORMAT OLLAMA
# ============================================================

def mcp_tools_to_ollama(mcp_tools):
    """
    Convertit les tools MCP dans le format attendu par Ollama.
    """

    tools = []

    for tool in mcp_tools.tools:

        # MCP fournit normalement inputSchema
        input_schema = tool.inputSchema

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": input_schema,
                },
            }
        )

    return tools


# ============================================================
# APPEL D'UN TOOL MCP
# ============================================================

async def call_mcp_tool(session, tool_name, arguments):
    """
    Appelle réellement un tool sur le MCP Server.
    """

    print(f"\n Appel du tool MCP : {tool_name}")
    print(f" Arguments : {arguments}")

    result = await session.call_tool(
        tool_name,
        arguments,
    )

    return result


# ============================================================
# EXTRACTION DU RESULTAT MCP
# ============================================================

def extract_mcp_result(result):
    """
    Transforme le résultat MCP en texte exploitable par le LLM.
    """

    contents = []

    for content in result.content:

        if hasattr(content, "text"):
            contents.append(content.text)

        else:
            contents.append(str(content))

    return "\n".join(contents)


# ============================================================
# AGENT
# ============================================================

async def ask_agent(session, tools, question):
    """
    Envoie une question au LLM et lui permet d'utiliser
    les tools MCP.
    """

    messages = [
        {
            "role": "system",
            "content": (
                "Tu es l'assistant énergétique EnergIA. "
                "Tu dois utiliser les outils disponibles lorsque "
                "la question de l'utilisateur nécessite des données "
                "provenant du système EnergIA. "
                "N'invente jamais une donnée qui peut être obtenue "
                "avec un outil. "
                "Après avoir obtenu les résultats des outils, "
                "réponds clairement en français."
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    # --------------------------------------------------------
    # PREMIER APPEL AU LLM
    # --------------------------------------------------------

    response = ollama_client.chat(
        model=MODEL,
        messages=messages,
        tools=tools,
    )

    message = response["message"]

    # Ajouter la réponse du LLM à l'historique
    messages.append(message)

    # --------------------------------------------------------
    # BOUCLE DE TOOL CALLING
    # --------------------------------------------------------

    while message.get("tool_calls"):

        for tool_call in message["tool_calls"]:

            function = tool_call["function"]

            tool_name = function["name"]
            arguments = function.get("arguments", {})

            # Certains modèles peuvent renvoyer les arguments
            # sous forme de JSON string.
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            # Appel du tool MCP
            result = await call_mcp_tool(
                session,
                tool_name,
                arguments,
            )

            result_text = extract_mcp_result(result)

            print("Résultat MCP :")
            print(result_text)

            # Ajouter le résultat du tool à la conversation
            messages.append(
                {
                    "role": "tool",
                    "content": result_text,
                }
            )

        # ----------------------------------------------------
        # LE LLM INTERPRÈTE LE RÉSULTAT
        # ----------------------------------------------------

        response = ollama_client.chat(
            model=MODEL,
            messages=messages,
            tools=tools,
        )

        message = response["message"]

        messages.append(message)

    # --------------------------------------------------------
    # REPONSE FINALE
    # --------------------------------------------------------

    return message.get("content", "")


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

async def main():

    print("Démarrage de l'agent EnergIA")
    print(f"Modèle : {MODEL}")
    print(f"Ollama : {OLLAMA_HOST}")
    print(f"MCP    : {MCP_URL}")

    # Connexion au MCP Server
    async with streamablehttp_client(MCP_URL) as streams:

        read_stream, write_stream, _ = streams

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            # Initialisation MCP
            await session.initialize()

            print("\n Connexion MCP établie")

            # Récupération des tools
            mcp_tools = await session.list_tools()

            print("\n Tools disponibles :")

            for tool in mcp_tools.tools:
                print(f"  - {tool.name}")

            # Conversion MCP → Ollama
            ollama_tools = mcp_tools_to_ollama(mcp_tools)

            print("\n Agent prêt !")
            print("Tape 'quit' pour quitter.\n")

            # ------------------------------------------------
            # BOUCLE DE CONVERSATION
            # ------------------------------------------------

            while True:

                question = input("Vous : ").strip()

                if question.lower() in {
                    "quit",
                    "exit",
                    "q",
                }:
                    print("Au revoir !")
                    break

                if not question:
                    continue

                try:

                    answer = await ask_agent(
                        session,
                        ollama_tools,
                        question,
                    )

                    print(f"\nEnergIA : {answer}\n")

                except Exception as e:

                    print(
                        f"\nErreur pendant le traitement : {e}\n"
                    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())