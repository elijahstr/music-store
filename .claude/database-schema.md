# Chinook Database Documentation

The Chinook database represents a digital music store, modeling the relationships between artists, albums, tracks, customers, employees, and sales.

## Entity Relationship Diagram

![Database Schema](sqlite-sample-database-color.jpg)

## Tables Overview

| Table | Records | Description |
|-------|---------|-------------|
| artists | 276 | Music artists/bands |
| albums | 359 | Albums released by artists |
| tracks | 3,539 | Individual songs/tracks |
| genres | 25 | Music genres (Rock, Jazz, etc.) |
| media_types | 5 | Format types (MPEG, AAC, etc.) |
| playlists | 18 | User-created playlists |
| playlist_track | 8,715 | Junction table linking playlists to tracks |
| customers | 61 | Store customers |
| employees | 9 | Store employees |
| invoices | 420 | Customer purchase invoices |
| invoice_items | 2,307 | Line items on invoices |

## Relationships

### Music Catalog

```
artists (1) ──────< albums (many)
                      │
                      └──< tracks (many)
                              │
               genres (1) ────┘
                              │
          media_types (1) ────┘
```

- **artists → albums**: One artist can have many albums (`albums.ArtistId` → `artists.ArtistId`)
- **albums → tracks**: One album contains many tracks (`tracks.AlbumId` → `albums.AlbumId`)
- **genres → tracks**: One genre categorizes many tracks (`tracks.GenreId` → `genres.GenreId`)
- **media_types → tracks**: One media type applies to many tracks (`tracks.MediaTypeId` → `media_types.MediaTypeId`)

### Playlists (Many-to-Many)

```
playlists (many) ──── playlist_track ────(many) tracks
```

- **playlists ↔ tracks**: Many-to-many relationship via `playlist_track` junction table
- A playlist can contain many tracks, and a track can appear in many playlists

### Sales & Customers

```
employees (1) ──────< customers (many)
     │                    │
     └─ ReportsTo (self)  └──< invoices (many)
                                    │
                                    └──< invoice_items (many)
                                              │
                               tracks (1) ────┘
```

- **employees → employees**: Self-referential for org hierarchy (`employees.ReportsTo` → `employees.EmployeeId`)
- **employees → customers**: Support rep assignment (`customers.SupportRepId` → `employees.EmployeeId`)
- **customers → invoices**: One customer can have many invoices (`invoices.CustomerId` → `customers.CustomerId`)
- **invoices → invoice_items**: One invoice has many line items (`invoice_items.InvoiceId` → `invoices.InvoiceId`)
- **tracks → invoice_items**: One track can be sold many times (`invoice_items.TrackId` → `tracks.TrackId`)

## Table Schemas

### artists
| Column | Type | Constraints |
|--------|------|-------------|
| ArtistId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| Name | NVARCHAR(120) | |

### albums
| Column | Type | Constraints |
|--------|------|-------------|
| AlbumId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| Title | NVARCHAR(160) | NOT NULL |
| ArtistId | INTEGER | NOT NULL, FK → artists |

### tracks
| Column | Type | Constraints |
|--------|------|-------------|
| TrackId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| Name | NVARCHAR(200) | NOT NULL |
| AlbumId | INTEGER | FK → albums |
| MediaTypeId | INTEGER | NOT NULL, FK → media_types |
| GenreId | INTEGER | FK → genres |
| Composer | NVARCHAR(220) | |
| Milliseconds | INTEGER | NOT NULL |
| Bytes | INTEGER | |
| UnitPrice | NUMERIC(10,2) | NOT NULL |

### genres
| Column | Type | Constraints |
|--------|------|-------------|
| GenreId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| Name | NVARCHAR(120) | |

### media_types
| Column | Type | Constraints |
|--------|------|-------------|
| MediaTypeId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| Name | NVARCHAR(120) | |

### playlists
| Column | Type | Constraints |
|--------|------|-------------|
| PlaylistId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| Name | NVARCHAR(120) | |

### playlist_track
| Column | Type | Constraints |
|--------|------|-------------|
| PlaylistId | INTEGER | PK, FK → playlists |
| TrackId | INTEGER | PK, FK → tracks |

### customers
| Column | Type | Constraints |
|--------|------|-------------|
| CustomerId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| FirstName | NVARCHAR(40) | NOT NULL |
| LastName | NVARCHAR(20) | NOT NULL |
| Company | NVARCHAR(80) | |
| Address | NVARCHAR(70) | |
| City | NVARCHAR(40) | |
| State | NVARCHAR(40) | |
| Country | NVARCHAR(40) | |
| PostalCode | NVARCHAR(10) | |
| Phone | NVARCHAR(24) | |
| Fax | NVARCHAR(24) | |
| Email | NVARCHAR(60) | NOT NULL |
| SupportRepId | INTEGER | FK → employees |

### employees
| Column | Type | Constraints |
|--------|------|-------------|
| EmployeeId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| LastName | NVARCHAR(20) | NOT NULL |
| FirstName | NVARCHAR(20) | NOT NULL |
| Title | NVARCHAR(30) | |
| ReportsTo | INTEGER | FK → employees (self) |
| BirthDate | DATETIME | |
| HireDate | DATETIME | |
| Address | NVARCHAR(70) | |
| City | NVARCHAR(40) | |
| State | NVARCHAR(40) | |
| Country | NVARCHAR(40) | |
| PostalCode | NVARCHAR(10) | |
| Phone | NVARCHAR(24) | |
| Fax | NVARCHAR(24) | |
| Email | NVARCHAR(60) | |

### invoices
| Column | Type | Constraints |
|--------|------|-------------|
| InvoiceId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| CustomerId | INTEGER | NOT NULL, FK → customers |
| InvoiceDate | DATETIME | NOT NULL |
| BillingAddress | NVARCHAR(70) | |
| BillingCity | NVARCHAR(40) | |
| BillingState | NVARCHAR(40) | |
| BillingCountry | NVARCHAR(40) | |
| BillingPostalCode | NVARCHAR(10) | |
| Total | NUMERIC(10,2) | NOT NULL |

### invoice_items
| Column | Type | Constraints |
|--------|------|-------------|
| InvoiceLineId | INTEGER | PRIMARY KEY AUTOINCREMENT |
| InvoiceId | INTEGER | NOT NULL, FK → invoices |
| TrackId | INTEGER | NOT NULL, FK → tracks |
| UnitPrice | NUMERIC(10,2) | NOT NULL |
| Quantity | INTEGER | NOT NULL |

## Example Queries

### Get all tracks by an artist
```sql
SELECT t.Name AS Track, al.Title AS Album, ar.Name AS Artist
FROM tracks t
JOIN albums al ON t.AlbumId = al.AlbumId
JOIN artists ar ON al.ArtistId = ar.ArtistId
WHERE ar.Name = 'AC/DC';
```

### Get customer purchase history
```sql
SELECT c.FirstName, c.LastName, i.InvoiceDate, i.Total
FROM customers c
JOIN invoices i ON c.CustomerId = i.CustomerId
ORDER BY i.InvoiceDate DESC;
```

### Get top-selling tracks
```sql
SELECT t.Name, COUNT(*) AS TimesSold, SUM(ii.Quantity) AS TotalQuantity
FROM tracks t
JOIN invoice_items ii ON t.TrackId = ii.TrackId
GROUP BY t.TrackId
ORDER BY TotalQuantity DESC
LIMIT 10;
```

### Get playlist contents
```sql
SELECT p.Name AS Playlist, t.Name AS Track, ar.Name AS Artist
FROM playlists p
JOIN playlist_track pt ON p.PlaylistId = pt.PlaylistId
JOIN tracks t ON pt.TrackId = t.TrackId
JOIN albums al ON t.AlbumId = al.AlbumId
JOIN artists ar ON al.ArtistId = ar.ArtistId
WHERE p.Name = 'Music';
```
