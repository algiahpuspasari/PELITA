import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from scipy.stats import spearmanr

DB = Path(__file__).with_name("pelita.db")

st.set_page_config(
    page_title="PELITA - Learning Gap",
    layout="wide",
)

# ---------- DATABASE ----------
def connect():
    return sqlite3.connect(DB, check_same_thread=False)


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS akademik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kode TEXT NOT NULL,
                jenjang TEXT NOT NULL,
                kelas TEXT,
                mapel TEXT NOT NULL,
                periode TEXT NOT NULL,
                kehadiran REAL NOT NULL,
                tugas REAL NOT NULL,
                nilai REAL NOT NULL,
                kompetensi TEXT NOT NULL,
                target REAL NOT NULL,
                nama TEXT NOT NULL DEFAULT ''
            )
            """
        )
        columns = {
            row[1] for row in conn.execute(
                "PRAGMA table_info(akademik)"
            ).fetchall()
        }
        if "nama" not in columns:
            conn.execute(
                "ALTER TABLE akademik ADD COLUMN nama TEXT NOT NULL DEFAULT ''"
            )


def get_data():
    with connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM akademik ORDER BY nama, kode, periode", conn
        )


def save_record(values):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO akademik
            (nama, kode, jenjang, kelas, mapel, periode,
             kehadiran, tugas, nilai, kompetensi, target)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )


def update_record(record_id, values):
    with connect() as conn:
        conn.execute(
            """
            UPDATE akademik
            SET nama=?, kode=?, jenjang=?, kelas=?, mapel=?, periode=?,
                kehadiran=?, tugas=?, nilai=?, kompetensi=?, target=?
            WHERE id=?
            """,
            (*values, record_id),
        )


def delete_record(record_id):
    with connect() as conn:
        conn.execute("DELETE FROM akademik WHERE id=?", (int(record_id),))


def delete_all_records():
    with connect() as conn:
        conn.execute("DELETE FROM akademik")


def make_alert(row):
    reasons = []
    if float(row["kehadiran"]) < 75:
        reasons.append("Kehadiran di bawah 75%")
    if float(row["nilai"]) < float(row["target"]):
        reasons.append("Nilai belum mencapai target")
    if float(row["tugas"]) < 70:
        reasons.append("Penyelesaian tugas perlu diperhatikan")

    if len(reasons) >= 2:
        status = "Perlu evaluasi lebih lanjut"
    elif len(reasons) == 1:
        status = "Perlu pendampingan"
    else:
        status = "Perlu pemantauan berkala"
    return status, "; ".join(reasons) if reasons else "Tidak ada indikator risiko"


def add_demo_data():
    demo = [
        ("Contoh Siswa 1", "P001", "SD", "5", "Matematika", "P1", 95, 90, 82, "Operasi hitung", 75),
        ("Contoh Siswa 1", "P001", "SD", "5", "Matematika", "P2", 90, 85, 78, "Operasi hitung", 75),
        ("Contoh Siswa 1", "P001", "SD", "5", "Matematika", "P3", 85, 80, 70, "Operasi hitung", 75),
        ("Contoh Siswa 2", "P002", "SMP", "8", "IPA", "P1", 90, 90, 80, "Sistem pencernaan", 75),
        ("Contoh Siswa 2", "P002", "SMP", "8", "IPA", "P2", 92, 85, 84, "Sistem pencernaan", 75),
        ("Contoh Siswa 2", "P002", "SMP", "8", "IPA", "P3", 95, 90, 88, "Sistem pencernaan", 75),
        ("Contoh Siswa 3", "P003", "SMA", "11", "Fisika", "P1", 80, 75, 68, "Gerak lurus", 75),
        ("Contoh Siswa 3", "P003", "SMA", "11", "Fisika", "P2", 78, 70, 65, "Gerak lurus", 75),
        ("Contoh Siswa 3", "P003", "SMA", "11", "Fisika", "P3", 75, 65, 60, "Gerak lurus", 75),
        ("Contoh Mahasiswa 1", "P004", "Perguruan Tinggi", "1", "Statistika", "P1", 95, 95, 90, "Statistik dasar", 75),
        ("Contoh Mahasiswa 1", "P004", "Perguruan Tinggi", "1", "Statistika", "P2", 95, 90, 88, "Statistik dasar", 75),
    ]
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO akademik
            (nama, kode, jenjang, kelas, mapel, periode,
             kehadiran, tugas, nilai, kompetensi, target)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            demo,
        )


def normalize_import_columns(frame):
    # Nama kolom Excel yang diterima: nama, kode, jenjang, kelas, mapel,
    # periode, kehadiran, tugas, nilai, kompetensi, target.
    frame = frame.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    required = [
        "nama", "kode", "jenjang", "kelas", "mapel", "periode",
        "kehadiran", "tugas", "nilai", "kompetensi", "target",
    ]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError("Kolom belum lengkap: " + ", ".join(missing))
    frame = frame[required].copy()
    for col in ["nama", "kode", "jenjang", "kelas", "mapel", "periode", "kompetensi"]:
        frame[col] = frame[col].fillna("").astype(str).str.strip()
    for col in ["kehadiran", "tugas", "nilai", "target"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    if frame[required].isna().any().any():
        raise ValueError("Ada sel kosong atau nilai angka yang tidak valid.")
    for col in ["kehadiran", "tugas", "nilai", "target"]:
        if not frame[col].between(0, 100).all():
            raise ValueError(f"Kolom {col} harus bernilai 0 sampai 100.")
    return frame


init_db()

# ---------- NAVIGATION ----------
st.sidebar.title("PELITA")
st.sidebar.caption("Pemetaan dan Evaluasi Learning Gap")
page = st.sidebar.radio(
    "Navigasi",
    ["Dashboard", "Input Data", "Kelola Data", "Analisis", "Peringatan Dini"],
)

df = get_data()
st.title("PELITA")
st.caption("Sistem Pemetaan dan Evaluasi Learning Gap Terintegrasi Akademik")

if "pesan_simpan" in st.session_state:
    st.success(st.session_state.pop("pesan_simpan"))

# ---------- DASHBOARD ----------
if page == "Dashboard":
    st.subheader("Dashboard Perkembangan Belajar")
    if df.empty:
        st.info("Belum ada data. Tambahkan data atau masukkan data simulasi.")
        if st.button("Masukkan Data Simulasi"):
            add_demo_data()
            st.success("Data simulasi berhasil ditambahkan.")
            st.rerun()
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Peserta Didik", int(df["kode"].nunique()))
        c2.metric("Rata-rata Nilai", f'{df["nilai"].mean():.1f}')
        c3.metric("Rata-rata Kehadiran", f'{df["kehadiran"].mean():.1f}%')
        c4.metric("Penyelesaian Tugas", f'{df["tugas"].mean():.1f}%')

        left, right = st.columns(2)
        with left:
            by_level = df.groupby("jenjang", as_index=False)["nilai"].mean()
            fig = px.bar(
                by_level, x="jenjang", y="nilai",
                title="Rata-rata Nilai per Jenjang",
                labels={"jenjang": "Jenjang", "nilai": "Rata-rata nilai"},
            )
            st.plotly_chart(fig, use_container_width=True)
        with right:
            period_order = sorted(df["periode"].dropna().unique())
            trend = df.groupby("periode", as_index=False)["nilai"].mean()
            trend["periode"] = pd.Categorical(
                trend["periode"], categories=period_order, ordered=True
            )
            trend = trend.sort_values("periode")
            fig = px.line(
                trend, x="periode", y="nilai", markers=True,
                title="Perkembangan Nilai per Periode",
                labels={"periode": "Periode", "nilai": "Rata-rata nilai"},
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Data Akademik Terbaru")
        display_cols = [
            "nama", "kode", "jenjang", "kelas", "mapel", "periode",
            "kehadiran", "tugas", "nilai", "kompetensi", "target",
        ]
        st.dataframe(
            df[display_cols].tail(10),
            use_container_width=True,
            hide_index=True,
        )

# ---------- INPUT DATA ----------
elif page == "Input Data":
    st.subheader("Tambah Data Akademik")
    with st.form("form_input", clear_on_submit=True):
        nama = st.text_input("Nama Lengkap Peserta Didik")
        kode = st.text_input("Kode peserta", placeholder="Contoh: P005")
        jenjang = st.selectbox(
            "Jenjang", ["SD", "SMP", "SMA", "SMK", "Perguruan Tinggi"]
        )
        kelas = st.text_input("Kelas / semester")
        mapel = st.text_input("Mata pelajaran / mata kuliah")
        periode = st.text_input("Periode", placeholder="Contoh: P1")
        kehadiran = st.number_input("Kehadiran (%)", 0.0, 100.0, 90.0)
        tugas = st.number_input("Penyelesaian tugas (%)", 0.0, 100.0, 80.0)
        nilai = st.number_input("Nilai akademik", 0.0, 100.0, 75.0)
        kompetensi = st.text_input(
            "Kompetensi yang dinilai", placeholder="Contoh: Operasi hitung"
        )
        target = st.number_input("Target kompetensi", 0.0, 100.0, 75.0)
        submitted = st.form_submit_button("Simpan Data", type="primary")

    if submitted:
        if not all([nama.strip(), kode.strip(), mapel.strip(), periode.strip(), kompetensi.strip()]):
            st.error("Lengkapi nama, kode, mata pelajaran, periode, dan kompetensi.")
        else:
            save_record((
                nama.strip(), kode.strip(), jenjang, kelas.strip(), mapel.strip(),
                periode.strip(), kehadiran, tugas, nilai, kompetensi.strip(), target,
            ))
            st.session_state["pesan_simpan"] = (
                f"Data akademik atas nama {nama.strip()} berhasil disimpan!"
            )
            st.rerun()

    st.divider()
    st.subheader("Unggah Data dari Excel")
    st.caption(
        "Gunakan file .xlsx dengan kolom: nama, kode, jenjang, kelas, mapel, "
        "periode, kehadiran, tugas, nilai, kompetensi, target."
    )
    uploaded = st.file_uploader("Pilih file Excel", type=["xlsx"])
    if uploaded is not None:
        if st.button("Impor Data Excel"):
            try:
                imported = normalize_import_columns(pd.read_excel(uploaded))
                with connect() as conn:
                    imported.to_sql("akademik", conn, if_exists="append", index=False)
                st.success(f"{len(imported)} baris data berhasil diimpor.")
                st.rerun()
            except Exception as exc:
                st.error(f"Impor gagal: {exc}")

# ---------- MANAGE DATA ----------
elif page == "Kelola Data":
    st.subheader("Kelola Data Akademik")
    if df.empty:
        st.info("Belum ada data untuk dikelola.")
    else:
        display_cols = [
            "nama", "kode", "jenjang", "kelas", "mapel", "periode",
            "kehadiran", "tugas", "nilai", "kompetensi", "target",
        ]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        st.markdown("### Ubah Data")
        selected_id = st.selectbox(
            "Pilih data berdasarkan nama dan ID",
            df["id"].tolist(),
            format_func=lambda rid: (
                f'{df.loc[df["id"] == rid, "nama"].iloc[0]} '
                f'(ID {rid} - {df.loc[df["id"] == rid, "mapel"].iloc[0]})'
            ),
        )
        selected = df[df["id"] == selected_id].iloc[0]
        with st.form("form_edit"):
            edit_nama = st.text_input("Nama", str(selected["nama"]))
            edit_kode = st.text_input("Kode peserta", str(selected["kode"]))
            levels = ["SD", "SMP", "SMA", "SMK", "Perguruan Tinggi"]
            edit_jenjang = st.selectbox(
                "Jenjang", levels, index=levels.index(selected["jenjang"])
            )
            edit_kelas = st.text_input("Kelas / semester", str(selected["kelas"] or ""))
            edit_mapel = st.text_input("Mata pelajaran", str(selected["mapel"]))
            edit_periode = st.text_input("Periode", str(selected["periode"]))
            edit_kehadiran = st.number_input(
                "Kehadiran (%)", 0.0, 100.0, float(selected["kehadiran"])
            )
            edit_tugas = st.number_input(
                "Penyelesaian tugas (%)", 0.0, 100.0, float(selected["tugas"])
            )
            edit_nilai = st.number_input(
                "Nilai", 0.0, 100.0, float(selected["nilai"])
            )
            edit_kompetensi = st.text_input(
                "Kompetensi", str(selected["kompetensi"])
            )
            edit_target = st.number_input(
                "Target", 0.0, 100.0, float(selected["target"])
            )
            update = st.form_submit_button("Simpan Perubahan")
        if update:
            if not all([edit_nama.strip(), edit_kode.strip(), edit_mapel.strip(),
                        edit_periode.strip(), edit_kompetensi.strip()]):
                st.error("Kolom teks wajib tidak boleh kosong.")
            else:
                update_record(selected_id, (
                    edit_nama.strip(), edit_kode.strip(), edit_jenjang,
                    edit_kelas.strip(), edit_mapel.strip(), edit_periode.strip(),
                    edit_kehadiran, edit_tugas, edit_nilai,
                    edit_kompetensi.strip(), edit_target,
                ))
                st.success("Data berhasil diperbarui.")
                st.rerun()

        st.markdown("### Hapus Satu Data")
        confirm_one = st.checkbox(f"Saya yakin ingin menghapus data ID {selected_id}")
        if st.button("Hapus Data", disabled=not confirm_one):
            delete_record(selected_id)
            st.success("Data berhasil dihapus.")
            st.rerun()

        st.markdown("### Hapus Seluruh Data")
        confirm_all = st.checkbox("Saya yakin ingin menghapus seluruh data akademik.")
        if st.button("Hapus Semua Data", type="secondary", disabled=not confirm_all):
            delete_all_records()
            st.success("Seluruh data akademik berhasil dihapus.")
            st.rerun()

    if not df.empty:
        st.divider()
        st.download_button(
            "Unduh seluruh data (CSV)",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="data_akademik_pelita.csv",
            mime="text/csv",
        )

# ---------- ANALYSIS ----------
elif page == "Analisis":
    st.subheader("Analisis Learning Gap")
    if df.empty:
        st.info("Belum ada data akademik untuk dianalisis.")
    else:
        st.write(
            "Analisis membandingkan nilai aktual peserta dengan target kompetensi. "
            "Hasilnya merupakan bahan pertimbangan pendidik, bukan keputusan otomatis."
        )
        level_options = ["Semua"] + sorted(df["jenjang"].dropna().unique().tolist())
        selected_level = st.selectbox("Pilih Jenjang", level_options)
        analysis = df.copy()
        if selected_level != "Semua":
            analysis = analysis[analysis["jenjang"] == selected_level]

        subject_options = ["Semua"] + sorted(analysis["mapel"].dropna().unique().tolist())
        selected_subject = st.selectbox("Pilih Mata Pelajaran", subject_options)
        if selected_subject != "Semua":
            analysis = analysis[analysis["mapel"] == selected_subject]

        analysis = analysis.copy()
        analysis["gap"] = (analysis["target"] - analysis["nilai"]).clip(lower=0)
        analysis["capaian"] = analysis["nilai"] >= analysis["target"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Rata-rata Nilai", f'{analysis["nilai"].mean():.2f}')
        c2.metric("Rata-rata Learning Gap", f'{analysis["gap"].mean():.2f}')
        c3.metric("Kompetensi Tercapai", f'{analysis["capaian"].mean() * 100:.1f}%')

        st.markdown("### Pemetaan Kompetensi")
        mapping = analysis.groupby("kompetensi", as_index=False).agg(
            rata_nilai=("nilai", "mean"),
            target=("target", "mean"),
            rata_gap=("gap", "mean"),
        )
        st.dataframe(mapping, use_container_width=True, hide_index=True)
        fig = px.bar(
            mapping, x="kompetensi", y=["rata_nilai", "target"],
            barmode="group", title="Perbandingan Nilai Aktual dan Target",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Hubungan Kehadiran dan Nilai")
        if len(analysis) >= 3 and analysis["kehadiran"].nunique() > 1 and analysis["nilai"].nunique() > 1:
            corr, p_value = spearmanr(analysis["kehadiran"], analysis["nilai"])
            st.metric("Korelasi Spearman", f"{corr:.3f}")
            st.caption(
                f"p-value: {p_value:.4f}. Korelasi menunjukkan hubungan, "
                "bukan sebab-akibat."
            )
        else:
            st.info("Data belum cukup bervariasi untuk menghitung korelasi.")

# ---------- EARLY WARNING ----------
elif page == "Peringatan Dini":
    st.subheader("Sistem Peringatan Dini Akademik")
    st.write(
        "Indikator ini membantu pendidik menentukan peserta yang perlu dipantau "
        "atau didampingi. Hasil perlu ditinjau bersama konteks pembelajaran."
    )
    if df.empty:
        st.info("Belum ada data akademik. Silakan masukkan data terlebih dahulu.")
    else:
        result = df.copy()
        alert_pairs = result.apply(make_alert, axis=1)
        result["status"] = [item[0] for item in alert_pairs]
        result["indikator"] = [item[1] for item in alert_pairs]

        def recommendation(status):
            if status == "Perlu evaluasi lebih lanjut":
                return "Evaluasi pembelajaran dan susun pendampingan individual."
            if status == "Perlu pendampingan":
                return "Lakukan pendampingan pada indikator yang belum memenuhi target."
            return "Pertahankan capaian dan lakukan pemantauan berkala."

        result["rekomendasi"] = result["status"].apply(recommendation)
        st.markdown("### Ringkasan Peringatan")
        c1, c2, c3 = st.columns(3)
        c1.metric("Perlu Evaluasi", int((result["status"] == "Perlu evaluasi lebih lanjut").sum()))
        c2.metric("Perlu Pendampingan", int((result["status"] == "Perlu pendampingan").sum()))
        c3.metric("Pemantauan Berkala", int((result["status"] == "Perlu pemantauan berkala").sum()))

        cols = [
            "nama", "kode", "jenjang", "mapel", "periode", "kehadiran",
            "tugas", "nilai", "target", "indikator", "status", "rekomendasi",
        ]
        st.markdown("### Hasil Identifikasi Peserta")
        st.dataframe(result[cols], use_container_width=True, hide_index=True)

        statuses = [
            "Semua", "Perlu evaluasi lebih lanjut",
            "Perlu pendampingan", "Perlu pemantauan berkala",
        ]
        chosen_status = st.selectbox("Filter status", statuses)
        filtered = result if chosen_status == "Semua" else result[result["status"] == chosen_status]
        st.dataframe(filtered[cols], use_container_width=True, hide_index=True)
        st.download_button(
            "Unduh Laporan Peringatan (CSV)",
            data=result.to_csv(index=False).encode("utf-8-sig"),
            file_name="laporan_peringatan_pelita.csv",
            mime="text/csv",
        )