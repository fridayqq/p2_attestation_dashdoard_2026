from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


DATA_DIR = Path(__file__).resolve().parent / "data"
LOGIN_USER = st.secrets["auth"]["username"]
LOGIN_PASS = st.secrets["auth"]["password"]


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def prepare_final(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = cleaned[cleaned["id_employee"].notna()].copy()
    cleaned["id_employee"] = cleaned["id_employee"].astype(int)
    return cleaned


def employee_label(row: pd.Series) -> str:
    name = row.get("fio_employee", "Без имени")
    employee_id = row.get("id_employee", "")
    return f"{name} ({employee_id})"


def render_selected_card(row: pd.Series) -> None:
    st.subheader("Сотрудник")
    st.markdown(f"**{row.get('fio_employee', '')}**")
    st.caption(f"ID: {row.get('id_employee', '')}")
    if "Участок" in row and pd.notna(row["Участок"]):
        st.write(row["Участок"])

    total = row.get("7")
    score = row.get("Unnamed: 10")
    if pd.notna(total):
        st.write(f"Сумма: {total}")
    if pd.notna(score):
        st.write(f"Сумма / 10: {score}")


def filtered_table(df: pd.DataFrame, employee_id: int) -> pd.DataFrame:
    if "id_employee" not in df.columns:
        return df.iloc[0:0]
    working = df.copy()
    working["id_employee"] = pd.to_numeric(working["id_employee"], errors="coerce").astype("Int64")
    filtered = working[working["id_employee"] == employee_id].copy()
    return filtered


def main() -> None:
    st.set_page_config(page_title="Аттестация 2025", layout="wide")
    st.title("Панель аттестации сотрудников")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("Вход")
        with st.form("login_form"):
            username = st.text_input("Логин")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")
        if submitted:
            if username == LOGIN_USER and password == LOGIN_PASS:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Неверный логин или пароль.")
        return

    final_path = DATA_DIR / "final.csv"
    if not final_path.exists():
        st.error("Файл final.csv не найден.")
        return

    final_df_raw = load_csv(final_path)
    final_df = prepare_final(final_df_raw)

    if final_df.empty:
        st.warning("Нет данных сотрудников в final.csv.")
        return

    employees = final_df.sort_values("fio_employee")
    options = {employee_label(row): row["id_employee"] for _, row in employees.iterrows()}

    if "selected_id" not in st.session_state:
        st.session_state.selected_id = next(iter(options.values()))

    selected_label = st.selectbox(
        "Выберите сотрудника",
        options=list(options.keys()),
        index=list(options.values()).index(st.session_state.selected_id),
    )
    st.session_state.selected_id = int(options[selected_label])

    selected_id = st.session_state.selected_id
    selected_row = final_df[final_df["id_employee"] == selected_id]
    if selected_row.empty:
        st.warning("Выбранный сотрудник не найден.")
        return

    render_selected_card(selected_row.iloc[0])

    st.subheader("Итоговая оценка")
    summary_vertical = (
        selected_row.transpose()
        .reset_index()
        .rename(columns={"index": "Показатель", selected_row.index[0]: "Значение"})
    )
    summary_vertical["Значение"] = summary_vertical["Значение"].astype(str)
    st.dataframe(summary_vertical, width="stretch", hide_index=True)

    st.subheader("Детализация по выбранному сотруднику")
    detail_files = sorted(
        path for path in DATA_DIR.glob("*.csv") if path.name != "final.csv"
    )

    if not detail_files:
        st.info("Дополнительные CSV файлы не найдены.")
        return

    tab_labels = {
        "detail_discipline_apr_dec2025": "Дисциплина",
        "detail_errors_apr_dec2025": "Ошибки",
        "detail_ranks_apr_dec2025": "Разряды",
        "performance_metrics_apr_dec2025": "Показатели",
    }
    tabs = st.tabs([tab_labels.get(path.stem, path.stem) for path in detail_files])
    for tab, path in zip(tabs, detail_files):
        with tab:
            df = load_csv(path)
            filtered = filtered_table(df, selected_id)
            st.caption(f"Фильтр: id_employee = {selected_id}")
            stem = path.stem.lower()
            if stem == "detail_discipline_apr_dec2025":
                total_points = filtered["discipline_points"].sum() if "discipline_points" in filtered.columns else 0
                st.write(f"Итого косяков (сумма discipline_points): {total_points}")
            elif stem == "detail_errors_apr_dec2025":
                st.write(f"Итого ошибок (кол-во записей): {len(filtered)}")
                if not filtered.empty:
                    if "area" in filtered.columns:
                        st.markdown("**Ошибки по участкам**")
                        area_counts = (
                            filtered["area"]
                            .fillna("Не указано")
                            .value_counts()
                            .reset_index()
                            .rename(columns={"index": "Участок", "area": "Кол-во"})
                        )
                        st.dataframe(area_counts, width="stretch", hide_index=True)
                    if "product" in filtered.columns:
                        st.markdown("**Ошибки по продуктам**")
                        product_counts = (
                            filtered["product"]
                            .fillna("Не указано")
                            .value_counts()
                            .reset_index()
                            .rename(columns={"index": "Продукт", "product": "Кол-во"})
                        )
                        st.dataframe(product_counts, width="stretch", hide_index=True)
                st.dataframe(
                    filtered,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "text_mistake": st.column_config.TextColumn(
                            "Комментарий",
                            width="large",
                            max_chars=None,
                        )
                    },
                )
            elif stem == "detail_ranks_apr_dec2025":
                if "mark" in filtered.columns and not filtered["mark"].empty:
                    avg_mark = filtered["mark"].mean()
                    st.write(f"Средний разряд (среднее mark): {avg_mark:.2f}")
                else:
                    st.write("Средний разряд (среднее mark): нет данных")
            elif stem == "performance_metrics_apr_dec2025":
                if "performance_points" in filtered.columns and not filtered.empty:
                    value = float(filtered.iloc[0]["performance_points"])
                    st.write(f"Итоговый балл: {value:.2f}")
                else:
                    st.write("Итоговый балл: нет данных")
            if stem != "detail_errors_apr_dec2025":
                st.dataframe(filtered, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
