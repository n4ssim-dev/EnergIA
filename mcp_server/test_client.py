import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    url = "http://127.0.0.1:8000/mcp"

    async with streamablehttp_client(url) as streams:
        read_stream, write_stream, _ = streams

        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("Outils disponibles :")
            for tool in tools.tools:
                print(f"- {tool.name}")

            get_regions_mcp = await session.call_tool("get_regions_mcp", {})
            get_centrales_mcp = await session.call_tool("get_centrales_mcp", {})

            print("\nRésultat de get_regions_mcp() :")
            print(get_regions_mcp)
            
            print("\nRésultat de get_centrales_mcp() :")
            print(get_centrales_mcp)


if __name__ == "__main__":
    asyncio.run(main())