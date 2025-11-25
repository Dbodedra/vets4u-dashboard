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
PASSWORD = "vets4upomeroy1"  # <--- CHANGE THIS IF YOU WANT A DIFFERENT PASSWORD

def check_password():
    """Returns True if the user has entered the correct password."""
    if st.session_state.get('password_correct', False):
        return True
    
    st.markdown("### 🔒 Login Required")
    pwd = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
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
        
        # Categorize Staff
        all_names = set(list(roster.keys()) + list(absences.keys()))
        
        for name in all_names:
            if name in absences:
                reason = absences[name]
                if "Late" in reason:
                    late_staff.append({'Name': name, 'Reason': reason, 'Role': ', '.join(roster.get(name, ['Unassigned']))})
                    # Late staff technically count for headcount if we assume they arrive, 
                    # but for safety we might want to flag them. 
                    # For this dashboard, we count them as active but show warning.
                    active_staff.append(name) 
                else:
                    sick_staff.append({'Name': name, 'Reason': reason})
            elif name in roster:
                active_staff.append(name)
        
        # Metrics Calculation
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
    st.set_page_config(page_title="Vets4u Dashboard", page_icon="💊", layout="wide")
    
    if not check_password():
        st.stop()
    
    app = Vets4uDashboard()
    
    st.title("💊 Vets4u Ops Center")

    # NEW TABS ORDER
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Live Dashboard", "✅ Staff Check-In & Holiday", "📅 Weekly Forecast", "⚙️ Admin"])

    selected_date = datetime.now()
    date_obj = datetime.combine(selected_date, datetime.min.time())

    # --- TAB 1: LIVE DASHBOARD (The "Pretty" View) ---
    with tab1:
        st.markdown(f"### 📅 {selected_date.strftime('%A %d %B %Y')}")
        result = app.analyze_day(date_obj)
        
        if result.get('status') == 'CLOSED':
            st.info("ℹ️ Store is CLOSED today (or no schedule set).")
        else:
            # 1. Main Status Banner
            status = result['overall_status']
            if status == "RED": 
                st.error(f"🛑 **STATUS: {status}** - CRITICAL ISSUES DETECTED")
            elif status == "AMBER": 
                st.warning(f"⚠️ **STATUS: {status}** - WARNING / NO BACKUP")
            else: 
                st.success(f"✅ **STATUS: {status}** - FULLY OPERATIONAL")

            # 2. Key Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Staff On-Site", result['count'])
            m2.metric("Openers", result['openers'])
            m3.metric("Checkers", result['checkers'])
            m4.metric("Absent/Late", len(result['sick_details']) + len(result['late_details']))

            # 3. Alerts Section
            if result['alerts']:
                for alert in result['alerts']: 
                    st.error(f"🚨 {alert}")

            st.markdown("---")
            
            # 4. Visual Team Board
            c_present, c_late, c_absent = st.columns(3)
            
            with c_present:
                with st.container(border=True):
                    st.markdown("### 🟢 On Duty")
                    if result['staff_details']:
                        for s in result['staff_details']:
                            st.markdown(f"**{s['Name']}**")
                            st.caption(f"{s['Role']}")
                    else:
                        st.write("No one checked in yet.")
            
            with c_late:
                with st.container(border=True):
                    st.markdown("### 🟠 Late / Warning")
                    if result['late_details']:
                        for l in result['late_details']:
                            st.warning(f"**{l['Name']}**")
                            st.caption(f"{l['Reason']}")
                    else:
                        st.success("No delays reported.")

            with c_absent:
                with st.container(border=True):
                    st.markdown("### 🔴 Absent / Sick / Holiday")
                    if result['sick_details']:
                        for m in result['sick_details']:
                            st.error(f"**{m['Name']}**")
                            st.caption(f"{m['Reason']}")
                    else:
                        st.success("Full attendance.")

    # --- TAB 2: CHECK-IN ---
    with tab2:
        staff_list = app.data['skills'].index.tolist() if 'skills' in app.data else []
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("👉 **Daily Check-In:** Use this when you arrive.")
            with st.form("daily_checkin_form"):
                if not staff_list: st.warning("No staff found.")
                name = st.selectbox("Your Name", staff_list)
                status = st.selectbox("Status", ["Present", "Sick", "Late", "Holiday"])
                note = st.text_input("Note (e.g. 15 mins late)")
                if st.form_submit_button("Submit Status"):
                    app.save_checkin(date_obj, name, status, note)
                    st.success("Updated!")
                    st.rerun()
        
        with c2:
            st.warning("✈️ **Future Holidays:** Book leave here.")
            with st.form("holiday_plan"):
                h_name = st.selectbox("Name", staff_list, key="h_name")
                d1, d2 = st.columns(2)
                h_start = d1.date_input("Start")
                h_end = d2.date_input("End")
                h_type = st.selectbox("Type", ["Holiday", "Sick (Planned)", "Training"])
                h_note = st.text_input("Reason")
                if st.form_submit_button("Book Holiday"):
                    app.save_holiday(h_name, h_start, h_end, h_type, h_note)
                    st.success("Holiday Booked!")
                    st.rerun()

    # --- TAB 3: FORECAST ---
    with tab3:
        st.write("#### 7-Day Outlook")
        forecast_df = app.get_weekly_forecast(date_obj)
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)

    # --- TAB 4: ADMIN ---
    with tab4:
        st.header("⚙️ Admin Panel")
        st.info("Manage Staff List & Build Schedules")
        
        admin_t1, admin_t2 = st.tabs(["👥 Manage Staff", "🗓️ Schedule Builder"])
        
        with admin_t1:
            if 'skills' in app.data:
                current_df = app.data['skills'].reset_index()
            else:
                current_df = pd.DataFrame(columns=["Name", "Opening", "Dispensing", "Second Check", "Vet Screening"])
            edited_df = st.data_editor(current_df, num_rows="dynamic", use_container_width=True)
            if st.button("Save Staff List"):
                if 'Name' in edited_df.columns:
                    edited_df = edited_df[edited_df['Name'].astype(str).str.strip() != '']
                    edited_df.set_index('Name', inplace=True)
                    app.save_skills(edited_df)
                    st.success("Saved!")
                    st.rerun()

        with admin_t2:
            staff_list = app.data['skills'].index.tolist() if 'skills' in app.data else []
            vet_options = staff_list + [p for p in ["Sue", "The Vets"] if p not in staff_list]
            
            c_a, c_b = st.columns(2)
            with c_a:
                sch_date = st.date_input("Schedule Date", datetime.now())
            with c_b:
                opener = st.multiselect("Opener", staff_list)
                downstairs = st.multiselect("Downstairs", staff_list)
                upstairs = st.multiselect("Upstairs", staff_list)
                vet = st.multiselect("Vet Screening", vet_options)
            
            if st.button("Save Schedule"):
                app.save_simple_schedule(sch_date, opener, downstairs, upstairs, vet)
                st.success(f"Schedule saved for {sch_date}")
                st.rerun()

            if 'simple_schedule' in app.data and not app.data['simple_schedule'].empty:
                st.markdown("### Existing Schedule")
                st.dataframe(app.data['simple_schedule'], hide_index=True)

if __name__ == "__main__":
    main()
