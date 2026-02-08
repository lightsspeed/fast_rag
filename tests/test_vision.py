from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.services.vision import vision_service

client = TestClient(app)

def test_analyze_image_endpoint():
    # Mock the vision service method
    with patch.object(vision_service, 'analyze_image', new_callable=AsyncMock) as mock_analyze:
        # Setup mock return value
        mock_analyze.return_value = {
            "analysis": "A beautiful landscape with mountains.",
            "model": "gemini-1.5-flash",
            "tokens_used": 0
        }
        
        # Test data
        payload = {
            "image_data": "data:image/jpeg;base64,...",
            "prompt": "Describe this image"
        }
        
        # Make request
        response = client.post("/api/v1/vision/analyze", json=payload)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["analysis"] == "A beautiful landscape with mountains."
        assert data["model"] == "gemini-1.5-flash"
        
        # Verify mock was called correctly
        mock_analyze.assert_called_once_with(
            image_data="data:image/jpeg;base64,...",
            prompt="Describe this image"
        )

def test_analyze_image_missing_key():
    # Mock the service to raise ValueError (simulating missing keys)
    with patch.object(vision_service, 'analyze_image', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.side_effect = ValueError("Google API key not configured. Please set GOOGLE_API_KEY.")
        
        payload = {
            "image_data": "data:image/jpeg;base64,..."
        }
        
        response = client.post("/api/v1/vision/analyze", json=payload)
        
        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "Google API key not configured" in response.json()["detail"]
