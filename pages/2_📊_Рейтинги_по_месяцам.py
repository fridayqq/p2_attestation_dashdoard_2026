"""Страница рейтингов по сотрудникам за декабрь 2025, январь и февраль 2026."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RATINGS_DIR = DATA_DIR / "ratings"

MONTHS = [
    ("2025_12", "Декабрь 2025"),
    ("2026_01", "Январь 2026"),
    ("2026_02", "Февраль 2026"),
]


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_ratings_data(month_key: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    """Загружает full, ratings и daily для месяца. Возвращает (full_df, ratings_df, daily_df)."""
    full_path = RATINGS_DIR / f"employee_daily_tasks_points_full_{month_key}.csv"
    ratings_path = RATINGS_DIR / f"employee_ratings_{month_key}.csv"
    daily_path = RATINGS_DIR / f"employee_points_daily_{month_key}.csv"

    full_df = load_csv(full_path) if full_path.exists() else None
    ratings_df = load_csv(ratings_path) if ratings_path.exists() else None
    daily_df = load_csv(daily_path) if daily_path.exists() else None

    return full_df, ratings_df, daily_df


def get_employees_from_full(full_dfs: list[pd.DataFrame | None]) -> list[tuple[int, str]]:
    """Собирает уникальный список (id_employee, fio_employee) из full-файлов."""
    seen: set[int] = set()
    result: list[tuple[int, str]] = []
    for df in full_dfs:
        if df is None or df.empty:
            continue
        if "id_employee" not in df.columns or "fio_employee" not in df.columns:
            continue
        for _, row in df.drop_duplicates("id_employee").iterrows():
            eid = int(row["id_employee"])
            if eid not in seen:
                seen.add(eid)
                fio = str(row.get("fio_employee", "Без имени"))
                result.append((eid, fio))
    return sorted(result, key=lambda x: x[1])


def main() -> None:
    st.set_page_config(page_title="Рейтинги по месяцам", layout="wide")
    st.title("Рейтинги по сотрудникам")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.warning("Войдите в систему на главной странице.")
        return

    all_full = []
    for month_key, _ in MONTHS:
        full_df, _, _ = load_ratings_data(month_key)
        all_full.append(full_df)

    employees = get_employees_from_full(all_full)
    if not employees:
        st.error("Нет данных сотрудников в файлах рейтингов.")
        return

    options = {f"{fio} ({eid})": eid for eid, fio in employees}
    selected_label = st.selectbox("Выберите сотрудника", options=list(options.keys()))
    selected_id = options[selected_label]

    st.divider()

    for month_key, month_label in MONTHS:
        full_df, ratings_df, daily_df = load_ratings_data(month_key)

        with st.expander(f"**{month_label}**", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Итоговый балл (ratings)**")
                if ratings_df is not None and not ratings_df.empty:
                    row = ratings_df[ratings_df["id_employee"] == selected_id]
                    if not row.empty:
                        mark = row.iloc[0]["mark"]
                        st.metric("Балл", f"{mark:.1f}")
                    else:
                        st.info("Нет данных")
                else:
                    st.info("Файл не найден")

            with col2:
                st.markdown("**Daily: среднее**")
                if daily_df is not None and not daily_df.empty:
                    emp_daily = daily_df[daily_df["id_employee"] == selected_id]
                    if not emp_daily.empty:
                        avg = emp_daily["points"].mean()
                        st.metric("Среднее баллов", f"{avg:.2f}")
                    else:
                        st.info("Нет данных")
                else:
                    st.info("Файл не найден")

            with col3:
                st.markdown("**Full: строк**")
                if full_df is not None and not full_df.empty:
                    emp_full = full_df[full_df["id_employee"] == selected_id]
                    st.metric("Записей", len(emp_full))
                else:
                    st.info("Файл не найден")

            st.markdown("**Daily — детализация по дням**")
            if daily_df is not None and not daily_df.empty:
                emp_daily = daily_df[daily_df["id_employee"] == selected_id]
                if not emp_daily.empty:
                    st.dataframe(
                        emp_daily,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "date": st.column_config.DateColumn("Дата", format="DD.MM.YYYY"),
                            "points": st.column_config.NumberColumn("Баллы", format="%.2f"),
                        },
                    )
                else:
                    st.info("Нет записей за выбранный месяц")
            else:
                st.info("Файл daily не найден")

            st.markdown("**Full — детализация по строкам**")
            if full_df is not None and not full_df.empty:
                emp_full = full_df[full_df["id_employee"] == selected_id]
                if not emp_full.empty:
                    st.dataframe(
                        emp_full,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "date": st.column_config.DateColumn("Дата", format="DD.MM.YYYY"),
                            "points": st.column_config.NumberColumn("Баллы", format="%.2f"),
                        },
                    )
                else:
                    st.info("Нет записей за выбранный месяц")
            else:
                st.info("Файл full не найден")

    st.divider()
    st.caption("Данные: employee_daily_tasks_points_full_*, employee_ratings_*, employee_points_daily_*")


if __name__ == "__main__":
    main()
