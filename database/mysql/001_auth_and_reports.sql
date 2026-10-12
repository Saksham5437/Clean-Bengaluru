CREATE DATABASE IF NOT EXISTS clean_bengaluru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE clean_bengaluru;

CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL UNIQUE,
  phone VARCHAR(24),
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('user', 'admin') NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
  id CHAR(64) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT sessions_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX sessions_user_idx (user_id),
  INDEX sessions_expiry_idx (expires_at)
);

CREATE TABLE IF NOT EXISTS reports (
  id CHAR(36) PRIMARY KEY,
  case_id VARCHAR(32) NOT NULL UNIQUE,
  user_id CHAR(36),
  source ENUM('citizen', 'bus_camera') NOT NULL,
  category VARCHAR(80) NOT NULL,
  description TEXT,
  location_label VARCHAR(240) NOT NULL,
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  evidence_url VARCHAR(500),
  density_score TINYINT UNSIGNED,
  severity ENUM('low', 'moderate', 'high', 'critical'),
  status ENUM('submitted', 'assigned', 'in_progress', 'resolved', 'rejected') NOT NULL DEFAULT 'submitted',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT reports_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX reports_status_idx (status),
  INDEX reports_user_idx (user_id)
);

CREATE TABLE IF NOT EXISTS report_events (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  report_id CHAR(36) NOT NULL,
  previous_status ENUM('submitted', 'assigned', 'in_progress', 'resolved', 'rejected'),
  new_status ENUM('submitted', 'assigned', 'in_progress', 'resolved', 'rejected') NOT NULL,
  actor_user_id CHAR(36),
  note VARCHAR(500),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT report_events_report_fk FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
  CONSTRAINT report_events_actor_fk FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX report_events_report_idx (report_id, created_at)
);

-- Create an admin through a controlled seed/migration process. Never hard-code a real password here.
