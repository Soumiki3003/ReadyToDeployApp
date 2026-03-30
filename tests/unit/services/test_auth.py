from app.services.auth import AuthService

def test_hash_password():
    service = AuthService()
    password = "secure_password"
    hashed = service.hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 10
    
def test_verify_password():
    service = AuthService()
    password = "secure_password"
    hashed = service.hash_password(password)
    
    assert service.verify_password(password, hashed) is True
    assert service.verify_password("wrong_password", hashed) is False
