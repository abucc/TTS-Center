import bcrypt

# Generate bcrypt hash for the user's password with 12 rounds
password = b"password"
salt = bcrypt.gensalt(12)
hashed = bcrypt.hashpw(password, salt)
print(hashed.decode('utf-8'))
