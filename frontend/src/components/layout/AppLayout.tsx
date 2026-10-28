import { NavLink, Outlet } from 'react-router-dom'
import styles from './AppLayout.module.css'

const links = [
  { to: '/', label: 'Dashboard', end: true, mark: '01' },
  { to: '/clients', label: 'Clients', mark: '02' },
  { to: '/bookings', label: 'Bookings', mark: '03' },
  { to: '/invoices', label: 'Invoices', mark: '04' },
  { to: '/documents', label: 'Documents', mark: '05' },
  { to: '/settings', label: 'Settings', mark: '06' },
]

export function AppLayout() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <NavLink to="/" className={styles.brand} aria-label="Photography Document Studio home">
          <span className={styles.brandMark} aria-hidden="true">
            <span className={styles.brandGlyph}>
              P<span className={styles.brandDot}>·</span>D
            </span>
          </span>
          <span className={styles.brandName}>
            Photography
            <br />
            Document Studio
          </span>
        </NavLink>
        <div className={styles.sideLabel}>WORKSPACE / LOCAL</div>
        <nav className={styles.navigation} aria-label="Main navigation">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}
            >
              <span className={styles.navMark}>{link.mark}</span>
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className={styles.sidebarFoot}>
          <span className={styles.localDot} />
          <div>
            <strong>Private by default</strong>
            <small>Data stays on this device.</small>
          </div>
        </div>
      </aside>
      <div className={styles.mainColumn}>
        <header className={styles.topbar}>
          <span className="eyebrow">Photography services / Business desk</span>
          <span className={styles.localBadge}>LOCAL · NO CLOUD</span>
        </header>
        <main className={styles.content}>
          <Outlet />
        </main>
        <footer className={styles.footer}>
          Studio records are stored locally. Keep your device backed up.
        </footer>
      </div>
    </div>
  )
}
