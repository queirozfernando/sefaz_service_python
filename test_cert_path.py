import os

pfx = r"C:\certs\bene.pfx"

print("Path:", repr(pfx))
print("Existe?", os.path.exists(pfx))
