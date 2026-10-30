"""Chat en la terminal.  Uso: python cli.py [--debug]"""
import argparse

from muertotron import Bot


def main() -> None:
    ap = argparse.ArgumentParser(description="Muertotron3000 en la terminal")
    ap.add_argument("--debug", action="store_true", help="muestra puntajes y reglas activadas")
    args = ap.parse_args()
    bot = Bot()
    print("Muertotron3000 — Día de Muertos en México. Escribe 'salir' para terminar.\n")
    while True:
        try:
            text = input("Tú: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.strip().lower() in {"salir", "exit", "quit"}:
            break
        r = bot.reply(text)
        print("\nMuertotron3000:", r.plain(), "\n")
        if args.debug:
            print(f"  [intent={r.intent} entrada={r.entry_id} confianza={r.confidence} debug={r.debug}]\n")


if __name__ == "__main__":
    main()
