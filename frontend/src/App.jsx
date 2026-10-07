import { useEffect, useMemo, useState } from 'react'
import {
  Bell,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  ChefHat,
  Clock3,
  CupSoda,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Menu,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Utensils,
  Users,
  X,
} from 'lucide-react'

const API = '/api'
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const shiftColors = { Morning: 'morning', Afternoon: 'afternoon', Evening: 'evening', Off: 'off' }

function api(path, options = {}) {
  return fetch(`${API}${path}`, options).then(async (response) => {
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || 'Something went wrong')
    return data
  })
}

function formatDate(dateString) {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(new Date(`${dateString}T12:00:00`))
}

function App() {
  const [staff, setStaff] = useState([])
  const [schedule, setSchedule] = useState([])
  const [menu, setMenu] = useState([])
  const [requests, setRequests] = useState([])
  const [weekStart, setWeekStart] = useState(() => {
    const today = new Date()
    const day = today.getDay() || 7
    today.setDate(today.getDate() - day + 1)
    return today.toISOString().slice(0, 10)
  })
  const [activeTab, setActiveTab] = useState('overview')
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ employee_id: '', request_date: '', meal: '', note: '' })
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [mobileNav, setMobileNav] = useState(false)
  const [authenticated, setAuthenticated] = useState(null)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  useEffect(() => {
    api('/auth/session').then((result) => setAuthenticated(result.authenticated)).catch(() => setAuthenticated(false))
  }, [])

  const loadData = async () => {
    try {
      const [staffData, scheduleData, menuData, requestData] = await Promise.all([
        api('/staff'), api(`/schedule?week_start=${weekStart}`), api('/menu'), api('/meal-requests'),
      ])
      setStaff(staffData)
      setSchedule(scheduleData)
      setMenu(menuData)
      setRequests(requestData)
      setForm((current) => ({ ...current, employee_id: staffData[0]?.id || '', request_date: new Date().toISOString().slice(0, 10) }))
    } catch (error) {
      setStatus(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (authenticated) loadData()
  }, [weekStart, authenticated])

  const staffById = useMemo(() => Object.fromEntries(staff.map((person) => [person.id, person])), [staff])
  const today = new Date().toISOString().slice(0, 10)
  const todayMenu = menu.find((item) => item.menu_date === today) || menu[0]
  const currentSchedule = schedule.filter((item) => item.weekday === new Date().getDay() - 1 || (new Date().getDay() === 0 && item.weekday === 6))
  const shiftsThisWeek = schedule.filter((item) => item.shift_type !== 'Off').length
  const offDays = schedule.filter((item) => item.is_off).length

  const submitRequest = async (event) => {
    event.preventDefault()
    setStatus('')
    try {
      await api('/meal-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      setStatus('Meal request sent successfully.')
      setModalOpen(false)
      setForm({ employee_id: '', request_date: today, meal: '', note: '' })
      loadData()
    } catch (error) {
      setStatus(error.message)
    }
  }

  const changeWeek = (amount) => {
    const date = new Date(`${weekStart}T12:00:00`)
    date.setDate(date.getDate() + amount * 7)
    setWeekStart(date.toISOString().slice(0, 10))
  }

  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'schedule', label: 'Weekly schedule', icon: CalendarDays },
    { id: 'menu', label: 'Daily menu', icon: Utensils },
    { id: 'requests', label: 'Meal requests', icon: ChefHat },
  ]

  const submitLogin = async (event) => {
    event.preventDefault()
    setLoginError('')
    setLoginLoading(true)
    try {
      await api('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm),
      })
      setAuthenticated(true)
      setLoginForm({ username: '', password: '' })
    } catch (error) {
      setLoginError(error.message)
    } finally {
      setLoginLoading(false)
    }
  }

  const logout = async () => {
    try {
      await api('/auth/logout', { method: 'POST' })
    } finally {
      setAuthenticated(false)
    }
  }

  if (authenticated === null) {
    return <div className="auth-loading"><div className="auth-spinner" /> Checking secure session…</div>
  }

  if (!authenticated) {
    return (
      <main className="login-page">
        <section className="login-card">
          <div className="login-brand"><div className="brand-mark"><Utensils size={24} /></div><div><strong>MAISON</strong><span>Restaurant operations</span></div></div>
          <span className="eyebrow">SECURE ACCESS</span>
          <h1>Welcome back</h1>
          <p>Sign in to view the team schedule, daily menu, and meal requests.</p>
          <form onSubmit={submitLogin}>
            <label>Username<input autoComplete="username" value={loginForm.username} onChange={(event) => setLoginForm({ ...loginForm, username: event.target.value })} required /></label>
            <label>Password<input type="password" autoComplete="current-password" value={loginForm.password} onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })} required /></label>
            {loginError && <div className="login-error">{loginError}</div>}
            <button className="primary-button login-button" disabled={loginLoading}>{loginLoading ? 'Signing in…' : 'Sign in securely'}</button>
          </form>
          <div className="security-note"><ShieldCheck size={16} /> Protected by a secure server-side session</div>
        </section>
      </main>
    )
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Utensils size={21} /></div>
          <div><strong>MAISON</strong><span>Restaurant operations</span></div>
          <button className="mobile-close" onClick={() => setMobileNav(false)} aria-label="Close menu"><X /></button>
        </div>
        <nav>
          <p className="nav-label">Workspace</p>
          {navItems.map(({ id, label, icon: Icon }) => (
            <button key={id} className={activeTab === id ? 'active' : ''} onClick={() => { setActiveTab(id); setMobileNav(false) }}>
              <Icon size={18} /> {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="support-card"><ShieldCheck size={20} /><div><strong>Team portal</strong><span>All systems operational</span></div></div>
          <button className="logout-button" onClick={logout}><LogOut size={16} /> Sign out</button>
          <div className="profile"><div className="avatar">AM</div><div><strong>Amelia Morgan</strong><span>Manager</span></div></div>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <button className="menu-button" onClick={() => setMobileNav(true)} aria-label="Open menu"><Menu /></button>
          <div className="search"><Search size={18} /><input aria-label="Search" placeholder="Search team, menu, or requests" /></div>
          <div className="top-actions"><button aria-label="Notifications"><Bell size={19} /><span className="notification-dot" /></button><div className="avatar small">AM</div></div>
        </header>

        <div className="content">
          <section className="page-heading">
            <div><span className="eyebrow">MAISON RESTAURANT</span><h1>{activeTab === 'overview' ? 'Good morning, Amelia' : navItems.find((item) => item.id === activeTab)?.label}</h1><p>Here is what is happening across your team this week.</p></div>
            <button className="primary-button" onClick={() => setModalOpen(true)}><Plus size={18} /> Request a meal</button>
          </section>

          {status && <div className="status-message" role="status">{status}</div>}
          {loading ? <div className="loading">Loading restaurant data…</div> : (
            <>
              {activeTab === 'overview' && <Overview staff={staff} schedule={schedule} menu={menu} requests={requests} shiftsThisWeek={shiftsThisWeek} offDays={offDays} todayMenu={todayMenu} setActiveTab={setActiveTab} />}
              {activeTab === 'schedule' && <Schedule staff={staff} schedule={schedule} weekStart={weekStart} changeWeek={changeWeek} staffById={staffById} />}
              {activeTab === 'menu' && <MenuSection menu={menu} today={today} />}
              {activeTab === 'requests' && <Requests requests={requests} staff={staff} onRequest={() => setModalOpen(true)} />}
            </>
          )}
        </div>
      </main>

      {modalOpen && (
        <div className="modal-backdrop" onMouseDown={() => setModalOpen(false)}>
          <form className="modal" onSubmit={submitRequest} onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-header"><div><span className="eyebrow">NEW REQUEST</span><h2>What would you like?</h2></div><button type="button" onClick={() => setModalOpen(false)}><X /></button></div>
            <label>Employee<select value={form.employee_id} onChange={(event) => setForm({ ...form, employee_id: Number(event.target.value) })} required>{staff.map((person) => <option key={person.id} value={person.id}>{person.name} · {person.role}</option>)}</select></label>
            <label>Date<input type="date" value={form.request_date} onChange={(event) => setForm({ ...form, request_date: event.target.value })} required /></label>
            <label>Meal request<textarea value={form.meal} onChange={(event) => setForm({ ...form, meal: event.target.value })} placeholder="Tell the kitchen what you would like to eat…" required /></label>
            <label>Note <span>(optional)</span><input value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} placeholder="Allergies or special requests" /></label>
            <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setModalOpen(false)}>Cancel</button><button type="submit" className="primary-button"><Send size={17} /> Submit request</button></div>
          </form>
        </div>
      )}
    </div>
  )
}

function Overview({ staff, schedule, menu, requests, shiftsThisWeek, offDays, todayMenu, setActiveTab }) {
  const pending = requests.filter((item) => item.status === 'Pending').length
  const roleCounts = staff.reduce((counts, person) => ({ ...counts, [person.role]: (counts[person.role] || 0) + 1 }), {})
  return (
    <div className="dashboard-grid">
      <article className="hero-card">
        <div className="hero-copy"><span className="hero-kicker"><Sparkles size={14} /> TODAY AT MAISON</span><h2>{todayMenu?.meal || 'Today’s menu is being prepared'}</h2><p>Served with {todayMenu?.dessert || 'the daily dessert'}</p><button onClick={() => setActiveTab('menu')}>View today’s menu <ChevronRight size={16} /></button></div>
        <div className="hero-illustration"><div className="dish"><Utensils size={55} /><span>Daily special</span></div></div>
      </article>
      <article className="stat-card"><div className="stat-icon green"><Users /></div><div><span>Team members</span><strong>{staff.length}</strong><small>2 managers · 10 kitchen staff</small></div></article>
      <article className="stat-card"><div className="stat-icon orange"><Clock3 /></div><div><span>Shifts this week</span><strong>{shiftsThisWeek}</strong><small>{schedule.length - offDays} scheduled hours</small></div></article>
      <article className="stat-card"><div className="stat-icon purple"><CalendarDays /></div><div><span>Days off</span><strong>{offDays}</strong><small>Across all team members</small></div></article>
      <article className="panel team-panel"><div className="panel-heading"><div><span className="eyebrow">TEAM</span><h2>Kitchen roles</h2></div><button onClick={() => setActiveTab('schedule')}>View schedule</button></div><div className="role-list">{Object.entries(roleCounts).map(([role, count]) => <div key={role}><span>{role}</span><div className="progress"><i style={{ width: `${count / staff.length * 100}%` }} /></div><strong>{count}</strong></div>)}</div></article>
      <article className="panel requests-panel"><div className="panel-heading"><div><span className="eyebrow">REQUESTS</span><h2>Meal orders</h2></div><span className={`pending-badge ${pending ? '' : 'clear'}`}>{pending} pending</span></div><div className="request-preview">{requests.slice(0, 3).map((request) => <div className="request-row" key={request.id}><div className="avatar small">{request.initials}</div><div><strong>{request.name}</strong><span>{request.meal}</span></div><span className={`status ${request.status.toLowerCase()}`}>{request.status}</span></div>)}</div></article>
      <article className="panel menu-preview"><div className="panel-heading"><div><span className="eyebrow">TODAY</span><h2>Daily menu</h2></div><button onClick={() => setActiveTab('menu')}>Details</button></div><div className="menu-item"><div className="menu-icon"><Utensils /></div><div><strong>{todayMenu?.meal}</strong><span>Dessert: {todayMenu?.dessert}</span></div></div></article>
    </div>
  )
}

function Schedule({ staff, schedule, weekStart, changeWeek, staffById }) {
  const days = weekdays.map((day, index) => {
    const date = new Date(`${weekStart}T12:00:00`)
    date.setDate(date.getDate() + index)
    return { name: day.slice(0, 3), date: date.toISOString().slice(0, 10), index }
  })
  return <article className="panel schedule-panel"><div className="schedule-toolbar"><div><span className="eyebrow">WEEKLY PLANNING</span><h2>{formatDate(weekStart)} – {formatDate(days[6].date)}</h2></div><div className="week-controls"><button onClick={() => changeWeek(-1)}><ChevronLeft /></button><button onClick={() => changeWeek(0)}>This week</button><button onClick={() => changeWeek(1)}><ChevronRight /></button></div></div><div className="schedule-grid">{days.map((day) => <div className="day-column" key={day.date}><div className="day-header"><span>{day.name}</span><strong>{new Date(`${day.date}T12:00:00`).getDate()}</strong></div>{staff.map((person) => { const item = schedule.find((entry) => entry.employee_id === person.id && entry.weekday === day.index); return <div className={`shift-card ${shiftColors[item?.shift_type || 'Off']}`} key={person.id}><div className="shift-person"><span className="avatar tiny">{person.initials}</span><div><strong>{person.name}</strong><small>{person.role}</small></div></div><div className="shift-time">{item?.is_off ? <><span className="off-dot" /> Off day</> : <><Clock3 size={13} /> {item?.start_time} – {item?.end_time}</>}</div></div> })}</div>)}</div></article>
}

function MenuSection({ menu, today }) {
  return <div className="menu-layout">{menu.map((item) => <article className={`menu-card ${item.menu_date === today ? 'today' : ''}`} key={item.id}><div className="date-block"><span>{new Date(`${item.menu_date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short' })}</span><strong>{new Date(`${item.menu_date}T12:00:00`).getDate()}</strong></div><div className="menu-content"><span className="eyebrow">{item.menu_date === today ? 'TODAY’S MENU' : 'DAILY MENU'}</span><h2>{item.meal}</h2><p>Dessert: {item.dessert}</p><small>Updated {new Date(item.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small></div><div className="menu-art"><CupSoda /></div></article>)}</div>
}

function Requests({ requests, staff, onRequest }) {
  return <article className="panel requests-full"><div className="panel-heading"><div><span className="eyebrow">MEAL REQUESTS</span><h2>Kitchen meal requests</h2></div><button className="primary-button" onClick={onRequest}><Plus size={17} /> New request</button></div><div className="request-table"><div className="table-head"><span>Employee</span><span>Request</span><span>Date</span><span>Status</span></div>{requests.map((request) => <div className="table-row" key={request.id}><div className="employee-cell"><span className="avatar tiny">{request.initials}</span><div><strong>{request.name}</strong><small>{request.role}</small></div></div><div><strong>{request.meal}</strong>{request.note && <small>{request.note}</small>}</div><span>{formatDate(request.request_date)}</span><span className={`status ${request.status.toLowerCase()}`}>{request.status}</span></div>)}</div>{staff.length === 0 && <div className="empty">No requests yet.</div>}</article>
}

export default App
