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
        # We define the files we expect
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
        # 1. Load or Create Skills Matrix (The most important file)
        if not os.path.exists(self.files['skills']):
            self.using_demo_data = True
            # Create default template with CORE STAFF including Rushil and Rak
            default_staff = [
                {"Name": "Dipesh", "Opening": "YES", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "Nidhesh", "Opening": "YES", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "Varsha", "Opening": "NO", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "VJ", "Opening": "NO", "Dispensing": "YES", "Second Check": "YES", "Vet Screening": "NO"},
                {"Name": "Rushil", "Opening": "NO", "Dispensing": "NO", "Second Check": "NO", "Vet Screening": "NO"}, # Added
                {"Name": "Rak", "Opening": "YES", "Dispensing": "NO", "Second Check": "NO", "Vet Screening": "NO"}    # Added
            ]
            pd.DataFrame(default_staff).to_csv(self.files['skills'], index=False)
        
        try:
            # Flexible loader for skills
            # We try to read it. If it fails (empty), we init empty DF
            try:
                # Attempt to find header row if it's the old complex format
                raw_skills = pd.read_csv(self.files['skills'], header=None, names=range(20))
                header_mask = raw_skills.apply(lambda x: x.astype(str).str.contains('Name', case=False).any() and 
                                                         x.astype(str).str.contains('Opening', case=False).any(), axis=1)
                if header_mask.any():
                    header_idx = header_mask.idxmax()
                    self.data['skills'] = pd.read_csv(self.files['skills'], header=header_idx)
                else:
                    # Assume simple format (created by app)
                    self.data['skills'] = pd.read_csv(self.files['skills'])
            except:
                 self.data['skills'] = pd.read_csv(self.files['skills'])

            # Clean up Skills DF
            if 'Name' in self.data['skills'].columns:
                self.data['skills']['Name'] = self.data['skills']['Name'].astype(str).str.strip()
                self.data['skills'].set_index('Name', inplace=True)
            
            # 2. Load Holiday Tracker
            if not os.path.exists(self.files['holidays']):
                 pd.DataFrame(columns=["Name", "Request Date", "Absence Start", "Absence End", "Type", "Status"]).to_csv(self.files['holidays'], index=False)
            
            # Robust load for holidays
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

            # 3. Load Schedule (Support both Old Complex and New Simple)
            if os.path.exists(SIMPLE_SCHEDULE_FILE):
                self.data['simple_schedule'] = pd.read_csv(SIMPLE_SCHEDULE_FILE)
            else:
                self.data['simple_schedule'] = pd.DataFrame(columns=["Date", "Opener", "Downstairs", "Upstairs", "Vet Screening"])

            # Attempt to load legacy file just in case
            if os.path.exists(self.files['schedule']):
                self.data['legacy_schedule'] = pd.read_csv(self.files['schedule'], header=None, names=range(20))
            else:
                self.data['legacy_schedule'] = None

            return True

        except Exception as e:
            st.error(f"❌ Error loading data: {e}")
            return False

    def get_scheduled_staff(self, query_date):
        """
        Logic: 
        1. Check 'Simple Schedule' (created in app). 
        2. If not found, check 'Legacy Schedule' (Excel upload).
        """
        q_date_str = query_date.strftime("%Y-%m-%d")
        
        # 1. Check Simple Schedule
        df_simple = self.data.get('simple_schedule')
        if df_simple is not None and not df_simple.empty:
            day_row = df_simple[df_simple['Date'] == q_date_str]
            if not day_row.empty:
                # Found entry!
                row = day_row.iloc[0]
                roster = {}
                for role in ['Opener', 'Downstairs', 'Upstairs', 'Vet Screening']:
                    if role in row and pd.notna(row[role]):
                        names = [n.strip() for n in str(row[role]).split(',')]
                        for n in names:
                            if n not in roster: roster[n] = []
                            roster[n].append(role)
                return roster, "Open"

        # 2. Fallback to Legacy Schedule (Complex Parser)
        df_legacy = self.data.get('legacy_schedule')
        if df_legacy is None or df_legacy.empty:
            return {}, "No Schedule Data"

        # Simplified legacy parser
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

    def get_absences_and_overrides(self, date_obj):
        """Combines Holiday Tracker + Manual Check-ins."""
        check_date = date_obj.strftime("%Y-%m-%d")
        absent_staff = {}
        
        # 1. File Absences (Holiday Tracker)
        # We need to handle ranges (Start Date -> End Date)
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

        # 2. Check-in Overrides (Daily Status)
        if os.path.exists(STATUS_FILE):
            df_s = pd.read_csv(STATUS_FILE)
            df_s = df_s[df_s['Date'] == check_date]
            for _, row in df_s.iterrows():
                status = row['Status']
                if status in ['Sick', 'Holiday', 'Absent']:
                    absent_staff[row['Name']] = f"Reported: {status}"
                elif status == 'Present':
                    if row['Name'] in absent_staff: del absent_staff[row['Name']]
        
        return absent_staff

    def analyze_day(self, date_obj):
        roster, status = self.get_scheduled_staff(date_obj)
        if status != "Open": return {'status': 'CLOSED', 'msg': status, 'count': 0}

        absences = self.get_absences_and_overrides(date_obj)
        active_staff = []
        missing_details = []

        for name in roster:
            if name in absences:
                reason = absences[name]
                missing_details.append(f"{name} ({reason})")
            else:
                active_staff.append(name)
                
        metrics = {'count': len(active_staff), 'openers': 0, 'checkers': 0, 'vet_screen': False, 'staff_details': [], 'missing_details': missing_details}
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
            
            if 'Vet Screening' in roster[name]: metrics['vet_screen'] = True
            metrics['staff_details'].append({'Name': name, 'Role': ', '.join(roster[name]), 'Skills': f"{'🔑' if can_open else ''}{'💊' if can_check else ''}"})

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
        """Saves to the permanent Holiday Tracker file."""
        new_row = {
            "Name": name,
            "Request Date": datetime.now().strftime("%Y-%m-%d"),
            "Absence Start": start_date.strftime("%Y-%m-%d"),
            "Absence End": end_date.strftime("%Y-%m-%d"),
            "Type": type,
            "Status": "Approved",
            "Notes": note
        }
        
        # Load existing
        if os.path.exists(self.files['holidays']):
            try:
                # Try simple load first
                df = pd.read_csv(self.files['holidays'])
            except:
                df = pd.DataFrame(columns=["Name", "Request Date", "Absence Start", "Absence End", "Type", "Status", "Notes"])
        else:
            df = pd.DataFrame(columns=["Name", "Request Date", "Absence Start", "Absence End", "Type", "Status", "Notes"])
            
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(self.files['holidays'], index=False)
        
        # Update memory
        self.data['holidays'] = df

    def save_simple_schedule(self, date_obj, opener, downstairs, upstairs, vet):
        # Load existing simple schedule
        if os.path.exists(SIMPLE_SCHEDULE_FILE):
            df = pd.read_csv(SIMPLE_SCHEDULE_FILE)
        else:
            df = pd.DataFrame(columns=["Date", "Opener", "Downstairs", "Upstairs", "Vet Screening"])
        
        date_str = date_obj.strftime("%Y-%m-%d")
        
        # Remove existing entry for this date if it exists
        df = df[df['Date'] != date_str]
        
        # Add new row
        new_row = {
            "Date": date_str,
            "Opener": ", ".join(opener),
            "Downstairs": ", ".join(downstairs),
            "Upstairs": ", ".join(upstairs),
            "Vet Screening": ", ".join(vet)
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(SIMPLE_SCHEDULE_FILE, index=False)
        
        # Reload data
        self.data['simple_schedule'] = df

    def save_skills(self, df):
        df.to_csv(self.files['skills'])
        self.data['skills'] = df

# --- Streamlit UI ---
def main():
    st.set_page_config(page_title="Vets4u Dashboard", page_icon="💊", layout="wide")
    
    # 🔒 CHECK PASSWORD FIRST
    if not check_password():
        st.stop()  # Stop here if not logged in
    
    app = Vets4uDashboard()
    
    st.title("💊 Vets4u Ops Center")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Daily Dashboard", "📅 Weekly Forecast", "📝 Staff Check-In & Holidays", "⚙️ Admin / Setup"])

    selected_date = datetime.now()
    date_obj = datetime.combine(selected_date, datetime.min.time())

    # --- TAB 1: DASHBOARD ---
    with tab1:
        st.caption(f"Showing status for Today: {selected_date.strftime('%A %d %b')}")
        result = app.analyze_day(date_obj)
        
        if result.get('status') == 'CLOSED':
            st.info("Store is CLOSED today (or no schedule set). Go to 'Admin / Setup' to add a schedule.")
        else:
            status = result['overall_status']
            if status == "RED": st.error(f"🛑 **STATUS: {status}** - CRITICAL ACTION REQUIRED")
            elif status == "AMBER": st.warning(f"⚠️ **STATUS: {status}** - CAUTION")
            else: st.success(f"✅ **STATUS: {status}** - OPERATIONAL")

            c1, c2, c3 = st.columns(3)
            c1.metric("Staff On-Site", result['count'])
            c2.metric("Openers", result['openers'])
            c3.metric("Checkers", result['checkers'])

            if result['alerts']:
                for alert in result['alerts']: st.error(alert)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**✅ Present**")
                for s in result['staff_details']: st.success(f"**{s['Name']}** {s['Skills']}")
            with col_b:
                st.markdown("**❌ Absent**")
                for m in result['missing_details']: st.error(f"~~{m}~~")

    # --- TAB 2: FORECAST ---
    with tab2:
        st.write("Next 5 Working Days")
        forecast_df = app.get_weekly_forecast(date_obj)
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)

    # --- TAB 3: CHECK-IN & HOLIDAYS ---
    with tab3:
        # If no staff loaded, show empty list
        staff_list = app.data['skills'].index.tolist() if 'skills' in app.data else []
        
        c_checkin, c_holiday = st.columns(2)
        
        # SECTION 1: TODAY'S STATUS
        with c_checkin:
            st.markdown("### 📍 Daily Check-In")
            st.info("Update status for **Today Only**.")
            with st.form("checkin"):
                if not staff_list:
                    st.warning("No staff found. Go to Admin.")
                
                name = st.selectbox("Name", staff_list)
                status = st.selectbox("Status", ["Present", "Sick", "Late", "Holiday"])
                note = st.text_input("Note (e.g. 10 mins late)")
                if st.form_submit_button("Update Today's Status"):
                    app.save_checkin(date_obj, name, status, note)
                    st.success("Updated!")
                    st.rerun()

        # SECTION 2: PLANNED HOLIDAYS
        with c_holiday:
            st.markdown("### ✈️ Plan Future Holiday")
            st.info("Book leave for future dates.")
            with st.form("holiday_plan"):
                h_name = st.selectbox("Staff Name", staff_list, key="h_name")
                c1, c2 = st.columns(2)
                h_start = c1.date_input("Start Date", min_value=datetime.now())
                h_end = c2.date_input("End Date", min_value=datetime.now())
                h_type = st.selectbox("Type", ["Holiday", "Sick (Planned)", "Training", "Other"])
                h_note = st.text_input("Notes")
                
                if st.form_submit_button("Book Absence"):
                    if h_end < h_start:
                        st.error("End date cannot be before start date.")
                    else:
                        app.save_holiday(h_name, h_start, h_end, h_type, h_note)
                        st.success(f"✅ Booked {h_type} for {h_name}!")
                        st.rerun()

    # --- TAB 4: ADMIN / SETUP ---
    with tab4:
        st.header("⚙️ System Setup")
        st.write("Use this tab if you don't have CSV files. You can manage everything here.")

        admin_tab1, admin_tab2 = st.tabs(["👥 Staff & Skills", "🗓️ Schedule Builder"])

        # 1. Staff Editor
        with admin_tab1:
            st.markdown("### Add/Edit Staff")
            st.write("Edit the table below to add new staff or change their skills. **Click the 'Name' column to add a name.**")
            
            # Load current skills df
            if 'skills' in app.data:
                current_df = app.data['skills'].reset_index()
            else:
                current_df = pd.DataFrame(columns=["Name", "Opening", "Dispensing", "Second Check", "Vet Screening"])

            edited_df = st.data_editor(current_df, num_rows="dynamic", use_container_width=True)

            if st.button("Save Staff Changes"):
                # Save back to file
                if 'Name' in edited_df.columns:
                    # Clean Empty Rows
                    edited_df = edited_df[edited_df['Name'].astype(str).str.strip() != '']
                    edited_df.set_index('Name', inplace=True)
                    app.save_skills(edited_df)
                    st.success("✅ Staff list updated! Refreshing...")
                    st.rerun()
                else:
                    st.error("Error: 'Name' column is missing.")

        # 2. Schedule Builder
        with admin_tab2:
            st.markdown("### Schedule Builder")
            st.write("Set who is working on a specific day.")
            
            # Get staff list
            staff_list = app.data['skills'].index.tolist() if 'skills' in app.data else []
            
            # Create special list for Vet Screening that includes "Sue" and "The Vets"
            # We filter duplicates just in case
            vet_options = staff_list + [p for p in ["Sue", "The Vets"] if p not in staff_list]
            
            col1, col2 = st.columns(2)
            with col1:
                sch_date = st.date_input("Select Date to Schedule", datetime.now())
            
            with col2:
                st.write("Select Staff for Roles:")
                opener = st.multiselect("Opener (First In)", staff_list)
                downstairs = st.multiselect("Downstairs Staff", staff_list)
                upstairs = st.multiselect("Upstairs Staff", staff_list)
                # UPDATED: Use the special list here
                vet = st.multiselect("Vet Screening", vet_options)
            
            if st.button("Save Schedule for Date"):
                app.save_simple_schedule(sch_date, opener, downstairs, upstairs, vet)
                st.success(f"✅ Schedule saved for {sch_date.strftime('%Y-%m-%d')}")
                st.rerun()

            # Show existing schedule
            st.markdown("#### Current Schedule Data")
            if 'simple_schedule' in app.data and not app.data['simple_schedule'].empty:
                st.dataframe(app.data['simple_schedule'], hide_index=True)
            else:
                st.info("No schedule data yet.")

if __name__ == "__main__":
    main()
    main()
