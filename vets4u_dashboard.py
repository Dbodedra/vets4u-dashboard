import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Try to import streamlit
try:
    import streamlit as st
except ImportError:
    print("⚠️  Streamlit is not installed. Please install it:")
    print("    pip install streamlit")
    sys.exit(1)

# Files
STATUS_FILE = "vets4u_daily_status.csv"
SIMPLE_SCHEDULE_FILE = "vets4u_simple_schedule.csv"

# --- SECURITY CONFIG ---
# Reverted to plain text comparison to fix login issue immediately.
PASSWORD = "vets4upomeroy1"

def check_password():
    """Returns True if the user has entered the correct password."""
    if st.session_state.get('password_correct', False):
        return True
    
    # Minimal Login Page
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("### 🔒 Vets4u Ops Login")
        pwd = st.text_input("Enter Password", type="password")
        if st.button("Login", use_container_width=True):
            if pwd == PASSWORD:
                st.session_state['password_correct'] = True
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    return False

class Vets4uDashboard:
    def __init__(self):
        self.files = {
            'schedule': "vets4u Tracker.xlsx - 4-Week Schedule.csv",
            'skills': "vets4u Tracker.xlsx - Skills Matrix.csv",
            'staff': "vets4u Tracker.xlsx - Staff Directory.csv",
            'holidays': "vets4u Tracker.xlsx - Holiday Tracker.csv"
        }
        self.data = {}
        self.using_demo_data = False
        self.ensure_data_loaded()

    def ensure_data_loaded(self):
        """Loads data. If files missing, creates templates."""
        # 1. Load or Create Skills Matrix
        if not os.path.exists(self.files['skills']):
            self.using_demo_data = True
            default_staff = [
                {"Name": "Dipesh", "Opening": "YES", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "Nidhesh", "Opening": "YES", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "Varsha", "Opening": "NO", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "VJ", "Opening": "NO", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "Rushil", "Opening": "NO", "Dispensing": "NO", "Second Check": "NO", "Vet Screening": "NO"},
                {"Name": "Rak", "Opening": "YES", "Dispensing": "NO", "Second Check": "NO", "Vet Screening": "NO"}
            ]
            pd.DataFrame(default_staff).to_csv(self.files['skills'], index=False)
        
        try:
            try:
                raw_skills = pd.read_csv(self.files['skills'], header=None, names=range(20))
                header_mask = raw_skills.apply(lambda x: x.astype(str).str.contains('Name', case=False).any() and 
                                                         x.astype(str).str.contains('Opening', case=False).any(), axis=1)
                if header_mask.any():
                    header_idx = header_mask.idxmax()
                    self.data['skills'] = pd.read_csv(self.files['skills'], header=header_idx)
                else:
                    self.data['skills'] = pd.read_csv(self.files['skills'])
            except:
                 self.data['skills'] = pd.read_csv(self.files['skills'])

            if 'Name' in self.data['skills'].columns:
                self.data['skills']['Name'] = self.data['skills']['Name'].astype(str).str.strip()
                self.data['skills'].set_index('Name', inplace=True)
            
            # 2. Load Holiday Tracker
            if not os.path.exists(self.files['holidays']):
                 pd.DataFrame(columns=["Name", "Request Date", "Absence Start", "Absence End", "Type", "Status"]).to_csv(self.files['holidays'], index=False)
            
            try:
                raw_holidays = pd.read_csv(self.files['holidays'], header=None, names=range(10))
                h_header_mask = raw_holidays.apply(lambda x: x.astype(str).str.contains('Absence Start', case=False).any(), axis=1)
                if h_header_mask.any():
                    h_idx = h_header_mask.idxmax()
                    self.data['holidays'] = pd.read_csv(self.files['holidays'], header=h_idx)
                else:
                    self.data['holidays'] = pd.read_csv(self.files['holidays'])
            except:
                self.data['holidays'] = pd.read_csv(self.files['holidays'])

            # 3. Load Schedule
            if os.path.exists(SIMPLE_SCHEDULE_FILE):
                self.data['simple_schedule'] = pd.read_csv(SIMPLE_SCHEDULE_FILE)
            else:
                self.data['simple_schedule'] = pd.DataFrame(columns=["Date", "Opener", "Downstairs", "Upstairs", "Vet Screening"])

            if os.path.exists(self.files['schedule']):
                self.data['legacy_schedule'] = pd.read_csv(self.files['schedule'], header=None, names=range(20))
            else:
                self.data['legacy_schedule'] = None

            return True

        except Exception as e:
            st.error(f"❌ Error loading data: {e}")
            return False

    def get_scheduled_staff(self, query_date):
        q_date_str = query_date.strftime("%Y-%m-%d")
        
        # Check Simple Schedule
        df_simple = self.data.get('simple_schedule')
        if df_simple is not None and not df_simple.empty:
            day_row = df_simple[df_simple['Date'] == q_date_str]
            if not day_row.empty:
                row = day_row.iloc[0]
                roster = {}
                for role in ['Opener', 'Downstairs', 'Upstairs', 'Vet Screening']:
                    if role in row and pd.notna(row[role]):
                        names = [n.strip() for n in str(row[role]).split(',')]
                        for n in names:
                            if n not in roster: roster[n] = []
                            roster[n].append(role)
                return roster, "Open"

        # Check Legacy Schedule
        df_legacy = self.data.get('legacy_schedule')
        if df_legacy is None or df_legacy.empty:
            return {}, "No Schedule Data"

        start_row = 5 
        for idx, row in df_legacy.iterrows():
            row_str = str(row.values)
            if "WEEK" in row_str and "CONFIRMED" in row_str:
                start_row = idx
                break
        
        day_idx = query_date.weekday()
        if day_idx > 4: return {}, "Weekend - Closed"
        col_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}
        col_idx = col_map[day_idx]
        
        if start_row + 5 >= len(df_legacy): return {}, "Schedule Data Error"

        roles_raw = {
            'Opener': df_legacy.iloc[start_row + 2, col_idx],
            'Downstairs': df_legacy.iloc[start_row + 3, col_idx],
            'Upstairs': df_legacy.iloc[start_row + 4, col_idx],
            'Vet Screening': df_legacy.iloc[start_row + 5, col_idx]
        }
        
        roster = {}
        for role, raw_names in roles_raw.items():
            if pd.isna(raw_names) or str(raw_names).lower() == 'nan': continue
            names = [n.strip() for n in str(raw_names).replace('+', ',').replace('/', ',').split(',')]
            for name in names:
                if name not in roster: roster[name] = []
                roster[name].append(role)
        
        return roster, "Open"

    def get_status_updates(self, date_obj):
        check_date = date_obj.strftime("%Y-%m-%d")
        absent_staff = {}
        extras = set()
        
        # 1. File Absences
        df_h = self.data['holidays']
        df_h.columns = [str(c).strip() for c in df_h.columns]
        
        if 'Absence Start' in df_h.columns and 'Absence End' in df_h.columns:
            for _, row in df_h.iterrows():
                try:
                    start = pd.to_datetime(row.get('Absence Start'))
                    end = pd.to_datetime(row.get('Absence End'))
                    current = pd.to_datetime(check_date)
                    
                    if str(row.get('Status')) == 'Approved' and start <= current <= end:
                        absent_staff[row['Name']] = row['Type']
                except:
                    continue

        # 2. Check-in Overrides
        if os.path.exists(STATUS_FILE):
            df_s = pd.read_csv(STATUS_FILE)
            df_s = df_s[df_s['Date'] == check_date]
            
            # Use dictionary to keep only the LATEST status per person
            status_map = {}
            for _, row in df_s.iterrows():
                status_map[row['Name']] = row['Status']
            
            for name, status in status_map.items():
                if status in ['Sick', 'Holiday', 'Late', 'Absent']:
                    absent_staff[name] = f"Reported: {status}"
                    if name in extras: extras.remove(name)
                elif status == 'Present':
                    if name in absent_staff: del absent_staff[name]
                    extras.add(name)
        
        return absent_staff, list(extras)

    def analyze_day(self, date_obj):
        roster, status = self.get_scheduled_staff(date_obj)
        absences, extras = self.get_status_updates(date_obj)

        if status != "Open": 
            if extras:
                status = "Open"
                roster = {}
            else:
                return {'status': 'CLOSED', 'msg': status, 'count': 0}

        for name in extras:
            if name not in roster:
                roster[name] = ["Flexible / Checked-In"]

        active_staff = []
        late_staff = []
        sick_staff = []
        
        all_names = set(list(roster.keys()) + list(absences.keys()))
        
        for name in all_names:
            if name in absences:
                reason = absences[name]
                if "Late" in reason:
                    late_staff.append({'Name': name, 'Reason': reason, 'Role': ', '.join(roster.get(name, ['Unassigned']))})
                    # Late staff are NOT active yet
                else:
                    sick_staff.append({'Name': name, 'Reason': reason})
            elif name in roster:
                active_staff.append(name)
        
        metrics = {
            'count': len(active_staff), 
            'openers': 0, 
            'checkers': 0, 
            'vet_screen': False, 
            'staff_details': [], 
            'late_details': late_staff,
            'sick_details': sick_staff
        }
        
        skills_df = self.data['skills']
        
        for name in active_staff:
            match = skills_df[skills_df.index.str.lower() == name.lower()]
            can_open, can_check = False, False
            if not match.empty:
                s = match.iloc[0]
                can_open = str(s.get('Opening', 'NO')).upper() == 'YES'
                can_check = str(s.get('Second Check', 'NO')).upper() == 'YES'
                if can_open: metrics['openers'] += 1
                if can_check: metrics['checkers'] += 1
            
            roles = roster.get(name, ["Checked-In"])
            if 'Vet Screening' in roles: metrics['vet_screen'] = True
            
            metrics['staff_details'].append({
                'Name': name, 
                'Role': ', '.join(roles), 
                'Skills': f"{'🔑' if can_open else ''}{'💊' if can_check else ''}"
            })

        alerts = []
        overall_status = "GREEN"
        if metrics['count'] < 2:
            alerts.append("CRITICAL: Staff count < 2. CLOSE PHARMACY.")
            overall_status = "RED"
        elif metrics['count'] == 2:
            alerts.append("WARNING: No Backup.")
            if overall_status != "RED": overall_status = "AMBER"
        if metrics['openers'] < 1:
            alerts.append("CRITICAL: No Opener.")
            overall_status = "RED"
        if metrics['checkers'] < 2: 
            alerts.append("CRITICAL: Dispensing Halted (<2 Checkers).")
            overall_status = "RED"
            
        metrics['alerts'] = alerts
        metrics['overall_status'] = overall_status
        return metrics

    def get_weekly_forecast(self, start_date):
        data = []
        for i in range(5):
            d = start_date + timedelta(days=i)
            if d.weekday() > 4: continue
            res = self.analyze_day(d)
            data.append({"Date": d.strftime("%Y-%m-%d"), "Day": d.strftime("%a"), "Staff Count": res.get('count', 0), "Status": res.get('overall_status', 'GRAY')})
        return pd.DataFrame(data)

    def save_checkin(self, date_obj, name, status, note):
        new_row = pd.DataFrame([{'Date': date_obj.strftime("%Y-%m-%d"), 'Name': name, 'Status': status, 'Note': note, 'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
        if not os.path.exists(STATUS_FILE): new_row.to_csv(STATUS_FILE, index=False)
        else: new_row.to_csv(STATUS_FILE, mode='a', header=False, index=False)
        
    def save_holiday(self, name, start_date, end_date, type, note):
        new_row = {
            "Name": name,
            "Request Date": datetime.now().strftime("%Y-%m-%d"),
            "Absence Start": start_date.strftime("%Y-%m-%d"),
            "Absence End": end_date.strftime("%Y-%m-%d"),
            "Type": type,
            "Status": "Approved",
            "Notes": note
        }
        
        if os.path.exists(self.files['holidays']):
            try:
                df = pd.read_csv(self.files['holidays'])
            except:
                df = pd.DataFrame(columns=["Name", "Request Date", "Absence Start", "Absence End", "Type", "Status", "Notes"])
        else:
            df = pd.DataFrame(columns=["Name", "Request Date", "Absence Start", "Absence End", "Type", "Status", "Notes"])
            
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(self.files['holidays'], index=False)
        self.data['holidays'] = df

    def save_simple_schedule(self, date_obj, opener, downstairs, upstairs, vet):
        if os.path.exists(SIMPLE_SCHEDULE_FILE):
            df = pd.read_csv(SIMPLE_SCHEDULE_FILE)
        else:
            df = pd.DataFrame(columns=["Date", "Opener", "Downstairs", "Upstairs", "Vet Screening"])
        
        date_str = date_obj.strftime("%Y-%m-%d")
        df = df[df['Date'] != date_str]
        
        new_row = {
            "Date": date_str,
            "Opener": ", ".join(opener),
            "Downstairs": ", ".join(downstairs),
            "Upstairs": ", ".join(upstairs),
            "Vet Screening": ", ".join(vet)
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(SIMPLE_SCHEDULE_FILE, index=False)
        self.data['simple_schedule'] = df

    def save_skills(self, df):
        df.to_csv(self.files['skills'])
        self.data['skills'] = df

# --- Streamlit UI ---
def main():
    st.set_page_config(page_title="Vets4u Ops", page_icon="💊", layout="wide")
    
    # IMPROVED CSS FOR CONTRAST AND READABILITY - Darker Tabs
    st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #f0f2f6;
    }
    
    /* Styling the metric cards - DARKER BACKGROUND for contrast */
    div[data-testid="stMetric"] {
        background-color: #E8EAF6; /* Darker grey/blue */
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        border: 1px solid #C5CAE9; /* Stronger border */
    }
    
    /* Force text inside metrics to be black */
    div[data-testid="stMetric"] label {
        color: #333333 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #000000 !important;
    }
    
    /* Styling the Team Status Containers (Green, Orange, Red boxes) */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: #FFFFFF;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    h3 {
        padding-top: 10px;
    }
    
    .stAlert {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* --- DARKER TABS CSS --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #E0E0E0; /* Default darker grey */
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #333333; /* Dark text */
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: #4B5563; /* Selected tab dark grey */
        color: #FFFFFF; /* Selected text white */
    }
    /* ----------------------- */

    </style>
    """, unsafe_allow_html=True)
    
    if not check_password():
        st.stop()
    
    app = Vets4uDashboard()
    
    col_logo, col_title, col_weather = st.columns([1, 4, 1])
    with col_logo:
        st.markdown("# 💊")
    with col_title:
        st.title("Vets4u Command Center")
        st.caption(f"Logged in as Admin • {datetime.now().strftime('%H:%M')} • Leicester, UK")
    with col_weather:
        st.markdown("""
        <div style="text-align: center; background: #F0F2F6; padding: 10px; border-radius: 10px; border: 1px solid #D1D5DB;">
            <h3 style="margin:0; color: #31333F;">☁️ 12°C</h3>
            <small style="color: #555;">Leicester, UK</small>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Live Dashboard", "✅ Check-In", "📅 Forecast", "👥 Staff Manager", "🗓️ Schedule Builder"])

    selected_date = datetime.now()
    date_obj = datetime.combine(selected_date, datetime.min.time())

    # --- TAB 1: LIVE DASHBOARD ---
    with tab1:
        st.markdown(f"### 📅 Status for {selected_date.strftime('%A %d %B %Y')}")
        result = app.analyze_day(date_obj)
        
        if result.get('status') == 'CLOSED':
            st.info("ℹ️ Store is CLOSED today (or no schedule set).")
        else:
            # 1. STATUS BANNER
            status = result['overall_status']
            if status == "RED": 
                st.error(f"🛑 **CRITICAL STATUS** - {len(result['sick_details'])} Absent - ACTION REQUIRED")
            elif status == "AMBER": 
                st.warning(f"⚠️ **WARNING LEVEL** - Operating on Minimum Staff")
            else: 
                st.success(f"✅ **OPERATIONAL** - All Systems Normal")

            # 2. KEY METRICS GRID
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("👥 Team On-Site", result['count'], "Target: 3")
            m2.metric("🔑 Openers", result['openers'], "Min: 1")
            m3.metric("💊 Checkers", result['checkers'], "Min: 2")
            m4.metric("⚠️ Issues", len(result['sick_details']) + len(result['late_details']), "Alerts", delta_color="inverse")

            st.divider()
            
            # 3. TOMORROW'S OPENER (UPDATED LOGIC)
            next_day = date_obj + timedelta(days=1)
            if next_day.weekday() > 4: # Sat/Sun
                next_day += timedelta(days=(7 - next_day.weekday()))
                
            # Rule: Dipesh on Thursday, Nidhesh on other days
            if next_day.weekday() == 3: # Thursday
                opener_name = "Dipesh"
            else:
                opener_name = "Nidhesh"
            
            st.info(f"🔑 **Next Opening Shift ({next_day.strftime('%A')}):** {opener_name}")

            # 4. MAIN TEAM BOARD
            c_present, c_late, c_absent = st.columns(3)
            
            with c_present:
                with st.container(border=True):
                    st.markdown("### 🟢 Active Team")
                    if result['staff_details']:
                        for s in result['staff_details']:
                            st.success(f"**{s['Name']}**")
                            st.caption(f"{s['Role']}")
                    else:
                        st.write("Waiting for staff...")
            
            with c_late:
                with st.container(border=True):
                    st.markdown("### 🟠 Late / Issues")
                    if result['late_details']:
                        for l in result['late_details']:
                            st.warning(f"**{l['Name']}**")
                            st.caption(f"Reason: {l['Reason']}")
                    else:
                        st.markdown("✅ *No delays*")

            with c_absent:
                with st.container(border=True):
                    st.markdown("### 🔴 Absent / Off")
                    if result['sick_details']:
                        for m in result['sick_details']:
                            st.error(f"**{m['Name']}**")
                            st.caption(f"{m['Reason']}")
                    else:
                        st.markdown("✅ *Full attendance*")

    # --- TAB 2: CHECK-IN & HOLIDAY ---
    with tab2:
        staff_list = app.data['skills'].index.tolist() if 'skills' in app.data else []
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("👉 **Daily Check-In**")
            with st.form("daily_checkin_form"):
                if not staff_list: st.warning("No staff found.")
                name = st.selectbox("👤 Your Name", staff_list)
                status = st.selectbox("📍 Status", ["Present", "Sick", "Late", "Holiday"])
                note = st.text_input("📝 Note (e.g. 15 mins late)")
                if st.form_submit_button("Update My Status"):
                    app.save_checkin(date_obj, name, status, note)
                    st.toast(f"Status updated for {name}!", icon="✅")
                    st.rerun()
        
        with c2:
            st.warning("✈️ **Book Future Leave**")
            with st.form("holiday_plan"):
                h_name = st.selectbox("👤 Name", staff_list, key="h_name")
                d1, d2 = st.columns(2)
                h_start = d1.date_input("📅 Start Date")
                h_end = d2.date_input("📅 End Date")
                h_type = st.selectbox("🏷 Type", ["Holiday", "Sick (Planned)", "Training"])
                h_note = st.text_input("📝 Reason")
                if st.form_submit_button("Book Holiday"):
                    app.save_holiday(h_name, h_start, h_end, h_type, h_note)
                    st.toast("Holiday Booked Successfully!", icon="✈️")
                    st.rerun()

    # --- TAB 3: FORECAST ---
    with tab3:
        st.write("#### 🔮 7-Day Staffing Outlook")
        forecast_df = app.get_weekly_forecast(date_obj)
        
        day_of_week = datetime.now().weekday()
        progress = (day_of_week + 1) / 5
        if progress > 1: progress = 1.0
        st.progress(progress, text=f"Week Progress: {int(progress*100)}%")
        
        st.bar_chart(forecast_df.set_index("Day")['Staff Count'], color="#00CC96")
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)

    # --- TAB 4: STAFF MANAGER ---
    with tab4:
        st.header("👥 Staff Manager")
        st.write("Add new staff or update skills here.")
        
        if 'skills' in app.data:
            current_df = app.data['skills'].reset_index()
        else:
            current_df = pd.DataFrame(columns=["Name", "Opening", "Dispensing", "Second Check", "Vet Screening"])
        
        edited_df = st.data_editor(current_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Save Staff List", type="primary"):
            if 'Name' in edited_df.columns:
                edited_df = edited_df[edited_df['Name'].astype(str).str.strip() != '']
                edited_df.set_index('Name', inplace=True)
                app.save_skills(edited_df)
                st.success("Staff list updated!")
                st.rerun()

    # --- TAB 5: SCHEDULE BUILDER ---
    with tab5:
        st.header("🗓️ Schedule Builder")
        st.write("Set the rota for future dates.")
        
        staff_list = app.data['skills'].index.tolist() if 'skills' in app.data else []
        vet_options = staff_list + [p for p in ["Sue", "The Vets"] if p not in staff_list]
        
        c_a, c_b = st.columns(2)
        with c_a:
            sch_date = st.date_input("Select Date to Schedule", datetime.now())
        with c_b:
            st.caption("Assign Roles:")
            opener = st.multiselect("🔑 Opener", staff_list)
            downstairs = st.multiselect("⬇️ Downstairs", staff_list)
            upstairs = st.multiselect("⬆️ Upstairs", staff_list)
            vet = st.multiselect("🐕 Vet Screening", vet_options)
        
        if st.button("💾 Save Schedule", type="primary"):
            app.save_simple_schedule(sch_date, opener, downstairs, upstairs, vet)
            st.success(f"Schedule saved for {sch_date}")
            st.rerun()

        if 'simple_schedule' in app.data and not app.data['simple_schedule'].empty:
            st.markdown("### 📋 Existing Schedule Data")
            st.dataframe(app.data['simple_schedule'], hide_index=True, use_container_width=True)

if __name__ == "__main__":
    main()
