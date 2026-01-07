# Vision Agent テスト用サンプル画像URL

## 既製品 (mass_product)

### スニーカー
```
https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800
```

### Apple製品 (MacBook)
```
https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=800
```

### 腕時計
```
https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800
```

---

## 一点物 (unique_item)

### 陶芸品
```
https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=800
```

### 絵画
```
https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?w=800
```

---

## 不明 (unknown)

### ぼやけた抽象画像
```
https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=800
```

---

## リクエスト例

### curl

```bash
curl -X POST "http://localhost:8000/api/v1/agent/vision_test" \
  -H "Content-Type: application/json" \
  -d '{"image_data": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800"}'
```

### Python (requests)

```python
import requests

url = "http://localhost:8000/api/v1/agent/vision_test"
payload = {
    "image_data": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800"
}

response = requests.post(url, json=payload)
print(response.json())
```
