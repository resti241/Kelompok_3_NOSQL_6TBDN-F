from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash

# Koneksi MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["shopee_rekomendasi"]

# Koleksi Produk
products = db["products"]
products.delete_many({})  # Kosongkan koleksi sebelum isi ulang

products.insert_many([
    {
        "_id": ObjectId(),
        "nama": "Mouse Wireless Logitech",
        "kategori": "Elektronik",
        "harga": 175000,
        "deskripsi": "Mouse tanpa kabel dengan sensor presisi tinggi",
        "tags": ["mouse", "logitech", "wireless"],
        "gambar": "/static/images/mouse.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Headset Bluetooth XYZ",
        "kategori": "Elektronik",
        "harga": 150000,
        "deskripsi": "Headset nirkabel dengan noise cancelling",
        "tags": ["headset", "bluetooth"],
        "gambar": "/static/images/headset.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Tas Selempang Wanita",
        "kategori": "Fashion",
        "harga": 120000,
        "deskripsi": "Tas model kekinian muat banyak barang",
        "tags": ["tas", "wanita", "fashion"],
        "gambar": "/static/images/tas.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Charger Fast Charging 25W",
        "kategori": "Elektronik",
        "harga": 99000,
        "deskripsi": "Charger cepat untuk semua jenis ponsel",
        "tags": ["charger", "fast", "elektronik"],
        "gambar": "/static/images/cas.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Power Bank 10000mAh Slim",
        "kategori": "Elektronik",
        "harga": 135000,
        "deskripsi": "Power bank kapasitas besar, ringan dan tipis",
        "tags": ["powerbank", "gadget", "elektronik"],
        "gambar": "/static/images/powerbank.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Sepatu Sneakers Pria",
        "kategori": "Fashion",
        "harga": 230000,
        "deskripsi": "Sneakers gaya sporty untuk pria",
        "tags": ["sepatu", "pria", "fashion"],
        "gambar": "/static/images/sepatu.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Mouse Wireless AJAZZ",
        "kategori": "Elektronik",
        "harga": 175000,
        "deskripsi": "Mouse tanpa kabel",
        "tags": ["mouse", "wireless"],
        "gambar": "/static/images/mouse3.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Jam Tangan Digital Sport",
        "kategori": "Aksesoris",
        "harga": 115000,
        "deskripsi": "Jam tangan tahan air dengan tampilan sporty",
        "tags": ["jam", "digital", "sport"],
        "gambar": "/static/images/jam.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Tumbler Stainless 500ml",
        "kategori": "Perlengkapan Rumah",
        "harga": 48000,
        "deskripsi": "Botol minum tahan panas dan dingin",
        "tags": ["tumbler", "minum", "rumah"],
        "gambar": "/static/images/tumbler.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Tumbler stainless",
        "kategori": "Perlengkapan Rumah",
        "harga": 120000,
        "deskripsi": "Botol minum aesthetic besar with sedotan dan pegangan",
        "tags": ["tumbler", "minum", "rumah", "stainless"],
        "gambar": "/static/images/tumbler2.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Mouse Wireless Robot",
        "kategori": "Elektronik",
        "harga": 175000,
        "deskripsi": "Mouse tanpa kabel",
        "tags": ["mouse", "wireless"],
        "gambar": "/static/images/mouse2.jpg",
        "likes": 0,
        "jumlah_beli": 0
    },
    {
        "_id": ObjectId(),
        "nama": "Tas Selempang Wanita Massdom",
        "kategori": "Fashion",
        "harga": 120000,
        "deskripsi": "Tas model kekinian muat banyak barang",
        "tags": ["tas", "wanita", "fashion"],
        "gambar": "/static/images/tas2.jpg",
        "likes": 0,
        "jumlah_beli": 0
    }
])

# Koleksi User
users = db["users"]
if not users.find_one({"username": "admin"}):
    users.insert_one({
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "preferensi": ["Elektronik", "Fashion"],
        "riwayat": [],
        "dilihat": []
    })

# Koleksi Interaksi
interactions = db["interactions"]
interactions.delete_many({})  # Kosongkan data interaksi

print("✅ Data produk, admin, dan interaksi berhasil diinisialisasi.")
