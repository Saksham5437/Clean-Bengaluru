# MySQL database

Run `001_auth_and_reports.sql` in MySQL 8+. Then configure the backend with:

```text
MYSQL_DATABASE_URL=mysql+pymysql://clean_app:change-me@127.0.0.1:3306/clean_bengaluru
```

The application creates ordinary user accounts through the registration endpoint. Admin accounts should be created by a controlled administrator or deployment seed process, never through public registration.

The migration also creates `sessions`, `reports`, and `report_events`. Evidence paths are stored as private application references; the API authorizes the report owner or an administrator before returning an image. Camera gateways write `bus_camera` reports through the separately keyed ingestion endpoint rather than public registration.
