from http import server
from livereload import Server, shell

if __name__ == "__main__":
    server = Server()
    server.watch("*.md", shell("ablog build"), delay=1)
    server.watch("posts/*.md", shell("ablog build"), delay=1)
    server.watch("*.py", shell("ablog build"), delay=1)
    server.watch("_static/*", shell("ablog build"), delay=1)
    server.watch("_templates/*", shell("ablog build"), delay=1)
    server.serve(root="docs/")