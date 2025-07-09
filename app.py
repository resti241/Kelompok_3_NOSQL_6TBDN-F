from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secretkey123'

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["shopee_rekomendasi"]
users_col = db["users"]
products_col = db["products"]
interactions_col = db["interactions"]

# Redis setup
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    tag = request.args.get('tag')
    sort_order = [("likes", -1), ("jumlah_beli", -1)]  # urutkan by likes dan pembelian

    if tag:
        produk_list = list(products_col.find({"tags": tag}).sort(sort_order))
    else:
        produk_list = list(products_col.find().sort(sort_order))

    for p in produk_list:
        p['_id'] = str(p['_id'])
        p['likes'] = p.get('likes', 0)
        p['jumlah_beli'] = p.get('jumlah_beli', 0)

    return render_template("index.html", produk=produk_list, user=session.get('username'))


@app.route('/produk/<id>')
def detail(id):
    try:
        id_asli = ObjectId(id)
        id_asli_str = str(id_asli)

        # Ambil produk utama
        produk = products_col.find_one({"_id": id_asli})
        if not produk:
            flash("Produk tidak ditemukan.")
            return redirect(url_for('index'))

        produk['_id'] = str(produk['_id'])

        # Simpan interaksi jika user login
        if 'user_id' in session:
            user_id = ObjectId(session['user_id'])
            users_col.update_one(
                {"_id": user_id},
                {"$push": {
                    "dilihat": {
                        "product_id": produk["_id"],
                        "timestamp": datetime.utcnow()
                    }
                }}
            )
            interaksi_data = {
                "user_id": str(user_id),
                "product_id": produk["_id"],
                "action": "view",
                "timestamp": datetime.utcnow().isoformat()
            }
            redis_client.rpush(f"interaksi:{user_id}", json.dumps(interaksi_data))
            interactions_col.insert_one(interaksi_data)

        # Produk serupa berdasarkan tag
        rekomendasi_cursor = products_col.find({
            "_id": {"$ne": id_asli},
            "tags": {"$in": produk.get("tags", [])}
        }).limit(4)
        rekomendasi = [{**p, "_id": str(p["_id"])} for p in rekomendasi_cursor]

        # Produk co-purchase (dibeli bersamaan)
        pipeline = [
            {"$match": {
                "action": "purchase",
                "product_id": id_asli_str
            }},
            {"$lookup": {
                "from": "interactions",
                "let": {"user_id": "$user_id"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$action", "purchase"]},
                                {"$eq": ["$user_id", "$$user_id"]},
                                {"$ne": ["$product_id", id_asli_str]}
                            ]
                        }
                    }}
                ],
                "as": "copurchase"
            }},
            {"$unwind": "$copurchase"},
            {"$group": {
                "_id": "$copurchase.product_id",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 4}
        ]

        copurchase_results = list(interactions_col.aggregate(pipeline))
        copurchase_products = []
        for item in copurchase_results:
            try:
                p = products_col.find_one({"_id": ObjectId(item["_id"])})
                if p:
                    p["_id"] = str(p["_id"])
                    copurchase_products.append(p)
            except Exception as err:
                print("Gagal mengambil produk copurchase:", err)
                continue

        return render_template(
            "detail.html",
            produk=produk,
            rekomendasi=rekomendasi,
            copurchase=copurchase_products
        )

    except InvalidId:
        flash("ID produk tidak valid.")
        return redirect(url_for('index'))
    except Exception as e:
        flash("Terjadi kesalahan saat membuka produk.")
        print("Error detail:", e)
        return redirect(url_for('index'))

@app.route('/produk/<id>/like', methods=['POST'])
def like_produk(id):
    try:
        produk_id = ObjectId(id)
        products_col.update_one(
            {"_id": produk_id},
            {"$inc": {"likes": 1}}
        )
        flash("Kamu menyukai produk ini!")
    except Exception as e:
        flash("Gagal menyukai produk.")
        print("Error like:", e)
    return redirect(request.referrer or url_for('index'))


@app.route('/keranjang')
def keranjang():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = users_col.find_one({"_id": ObjectId(user_id)})

    keranjang = user.get('keranjang', [])
    produk_keranjang = []
    for item in keranjang:
        produk = products_col.find_one({"_id": ObjectId(item['product_id'])})
        if produk:
            produk['_id'] = str(produk['_id'])
            produk['kuantitas'] = item.get('kuantitas', 1)
            produk_keranjang.append(produk)

    return render_template("keranjang.html", produk_keranjang=produk_keranjang)

@app.route('/keranjang/tambah', methods=['POST'])
def tambah_keranjang():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.")
        return redirect(url_for('login'))

    user_id = ObjectId(session['user_id'])
    product_id = ObjectId(request.form['product_id'])

    user = users_col.find_one({"_id": user_id})
    keranjang = user.get('keranjang', [])

    found = False
    for item in keranjang:
        if item['product_id'] == product_id:
            item['kuantitas'] = item.get('kuantitas', 1) + 1
            found = True
            break

    if not found:
        keranjang.append({"product_id": product_id, "kuantitas": 1, "timestamp": datetime.utcnow()})

    users_col.update_one({"_id": user_id}, {"$set": {"keranjang": keranjang}})

    interaksi_data = {
        "user_id": str(user_id),
        "product_id": str(product_id),
        "action": "keranjang",
        "timestamp": datetime.utcnow().isoformat()
    }

    redis_client.rpush(f"interaksi:{user_id}", json.dumps(interaksi_data))
    interactions_col.insert_one(interaksi_data)

    flash("Produk ditambahkan ke keranjang.")
    return redirect(request.referrer or url_for('index'))

@app.route('/keranjang/hapus', methods=['POST'])
def hapus_dari_keranjang():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    selected_ids = request.form.getlist('selected_ids')
    user_id = ObjectId(session['user_id'])
    user = users_col.find_one({"_id": user_id})

    keranjang_baru = [item for item in user.get('keranjang', []) if str(item['product_id']) not in selected_ids]
    users_col.update_one({"_id": user_id}, {"$set": {"keranjang": keranjang_baru}})

    flash("Produk berhasil dihapus dari keranjang.")
    return redirect(url_for('keranjang'))

@app.route('/keranjang/update_kuantitas', methods=['POST'])
def update_kuantitas():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    aksi_raw = request.form.get('aksi')  # contoh: 'tambah-60f...'
    if not aksi_raw or '-' not in aksi_raw:
        return redirect(url_for('keranjang'))

    jenis, produk_id = aksi_raw.split('-', 1)
    user_id = ObjectId(session['user_id'])
    user = users_col.find_one({"_id": user_id})
    keranjang = user.get('keranjang', [])

    for item in keranjang:
        if str(item['product_id']) == produk_id:
            if jenis == 'tambah':
                item['kuantitas'] = item.get('kuantitas', 1) + 1
            elif jenis == 'kurangi':
                item['kuantitas'] = max(1, item.get('kuantitas', 1) - 1)
            break

    users_col.update_one({"_id": user_id}, {"$set": {"keranjang": keranjang}})
    return redirect(url_for('keranjang'))


@app.route('/beli_sekarang', methods=['POST'])
def beli_sekarang():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    print("📦 Form Data:", request.form)
    user_id = ObjectId(session['user_id'])
    produk = []
    total = 0

    product_id = request.form.get('product_id')
    selected_ids = request.form.getlist('selected_ids')

    if product_id:
        # Beli langsung dari tombol beli atau beli lagi
        try:
            obj_id = ObjectId(product_id)
        except Exception:
            flash("ID produk tidak valid.")
            return redirect(url_for('index'))

        p = products_col.find_one({"_id": obj_id})
        if p:
            str_id = str(p['_id'])
            qty = request.form.get(f"kuantitas_{str_id}") or request.form.get("kuantitas") or 1
            try:
                qty = int(qty)
            except ValueError:
                qty = 1
            p['_id'] = str_id
            p['kuantitas'] = max(1, qty)
            produk.append(p)
            total += p['harga'] * p['kuantitas']
        else:
            flash("Produk tidak ditemukan.")
            return redirect(url_for('index'))

    elif selected_ids:
        # Beli dari keranjang (yang dipilih)
        user = users_col.find_one({"_id": user_id})
        keranjang = user.get('keranjang', [])
        for pid in selected_ids:
            try:
                obj_id = ObjectId(pid)
            except Exception:
                continue

            for item in keranjang:
                if str(item['product_id']) == pid:
                    p = products_col.find_one({"_id": obj_id})
                    if p:
                        str_id = str(p['_id'])
                        qty = request.form.get(f"kuantitas_{str_id}", item.get('kuantitas', 1))
                        try:
                            qty = int(qty)
                        except ValueError:
                            qty = item.get('kuantitas', 1)
                        p['_id'] = str_id
                        p['kuantitas'] = max(1, qty)
                        produk.append(p)
                        total += p['harga'] * p['kuantitas']
                    break

    if not produk:
        flash("Tidak ada produk yang dipilih.")
        return redirect(url_for('index'))

    return render_template("beli_sekarang.html", produk=produk, total=total)


@app.route('/proses_pembayaran', methods=['POST'])
def proses_pembayaran():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    metode = request.form.get('metode_pembayaran')
    user_id = ObjectId(session['user_id'])

    total = 0
    index = 0
    produk_dibeli = []

    while True:
        produk_id_key = f'produk_id_{index}'
        if produk_id_key not in request.form:
            break

        produk_id = request.form.get(produk_id_key)
        kuantitas_str = request.form.get(f'kuantitas_{produk_id}', '1')
        try:
            kuantitas = max(1, int(kuantitas_str))
        except ValueError:
            kuantitas = 1

        produk = products_col.find_one({"_id": ObjectId(produk_id)})
        if produk:
            harga = produk['harga']
            total += harga * kuantitas
            produk_dibeli.append((produk_id, kuantitas))

            # Tambah jumlah_beli
            products_col.update_one(
                {"_id": ObjectId(produk_id)},
                {"$inc": {"jumlah_beli": kuantitas}}
            )

            # Tambah ke riwayat (satu entry per item)
            for _ in range(kuantitas):
                users_col.update_one(
                    {"_id": user_id},
                    {"$push": {
                        "riwayat": {
                            "product_id": ObjectId(produk_id),
                            "timestamp": datetime.utcnow()
                        }
                    }}
                )

                # Simpan interaksi ke Redis & MongoDB
                interaksi_data = {
                    "user_id": str(user_id),
                    "product_id": produk_id,
                    "action": "purchase",
                    "timestamp": datetime.utcnow().isoformat()
                }
                redis_client.rpush(f"interaksi:{user_id}", json.dumps(interaksi_data))
                interactions_col.insert_one(interaksi_data)

        index += 1

    # Bersihkan keranjang
    users_col.update_one({"_id": user_id}, {"$set": {"keranjang": []}})

    flash(f"Pembayaran berhasil dengan metode: {metode.upper()} sebesar Rp{total:,}. Terima kasih telah berbelanja!")
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        if users_col.find_one({'username': username}):
            flash("Username sudah digunakan.")
        else:
            users_col.insert_one({
                'username': username,
                'password': password,
                'preferensi': [],
                'riwayat': [],
                'dilihat': [],
                'keranjang': []
            })
            flash("Registrasi berhasil, silakan login.")
            return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_col.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            flash("Username atau password salah.")
    return render_template("login.html")

@app.route('/riwayat')
def riwayat():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = ObjectId(session['user_id'])
    user = users_col.find_one({"_id": user_id})
    riwayat_data = user.get('riwayat', [])

    history = []
    for entry in riwayat_data:
        produk = products_col.find_one({"_id": entry['product_id']})
        if produk:
            history.append({
                "_id": str(produk["_id"]),  # ✅ ubah ke string!
                "nama": produk["nama"],
                "harga": produk["harga"],
                "gambar": produk["gambar"],
                "timestamp": entry.get("timestamp", datetime.utcnow())
            })

    return render_template("riwayat.html", history=history)

@app.route('/hapus_riwayat', methods=['POST'])
def hapus_riwayat():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = ObjectId(session['user_id'])
    produk_id = request.form.get('product_id')
    timestamp = request.form.get('timestamp')

    # Konversi timestamp kembali ke datetime jika diperlukan
    from dateutil.parser import parse as parse_date
    ts = parse_date(timestamp)

    users_col.update_one(
        {"_id": user_id},
        {"$pull": {"riwayat": {"product_id": ObjectId(produk_id), "timestamp": ts}}}
    )
    flash("Riwayat berhasil dihapus.")
    return redirect(url_for('riwayat'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
