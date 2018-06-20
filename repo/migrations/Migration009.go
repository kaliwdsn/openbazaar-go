package migrations

import (
	"database/sql"
	"path"

	"os"

	_ "github.com/mutecomm/go-sqlcipher"
)

type Migration009 struct{}

func (Migration009) Up(repoPath string, dbPassword string, testnet bool) (err error) {
	db, err := newDB(repoPath, dbPassword, testnet)
	if err != nil {
		return err
	}

	err = withTransaction(db, func(tx *sql.Tx) error {
		for _, stmt := range []string{
			"ALTER TABLE cases ADD COLUMN coinType text;",
			"ALTER TABLE sales ADD COLUMN coinType text;",
			"ALTER TABLE purchases ADD COLUMN coinType text;",
			"ALTER TABLE cases ADD COLUMN paymentCoin text;",
			"ALTER TABLE sales ADD COLUMN paymentCoin text;",
			"ALTER TABLE purchases ADD COLUMN paymentCoin text;",
		} {
			_, err := tx.Exec(stmt)
			if err != nil {
				return err
			}
		}
		return nil
	})
	if err != nil {
		return err
	}

	err = writeRepoVer(repoPath, 9)
	if err != nil {
		return err
	}
	return nil
}

func (Migration009) Down(repoPath string, dbPassword string, testnet bool) error {
	var dbPath string
	if testnet {
		dbPath = path.Join(repoPath, "datastore", "testnet.db")
	} else {
		dbPath = path.Join(repoPath, "datastore", "mainnet.db")
	}
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return err
	}
	if dbPassword != "" {
		p := "pragma key='" + dbPassword + "';"
		db.Exec(p)
	}
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	stmt1, err := tx.Prepare("ALTER TABLE sales RENAME TO temp_sales;")
	if err != nil {
		return err
	}
	defer stmt1.Close()
	_, err = stmt1.Exec()
	if err != nil {
		tx.Rollback()
		return err
	}
	stmt2, err := tx.Prepare(`create table sales (orderID text primary key not null, contract blob, state integer, read integer, timestamp integer, total integer, thumbnail text, buyerID text, buyerHandle text, title text, shippingName text, shippingAddress text, paymentAddr text, funded integer, transactions blob);`)
	if err != nil {
		return err
	}
	defer stmt2.Close()
	_, err = stmt2.Exec()
	if err != nil {
		tx.Rollback()
		return err
	}
	stmt3, err := tx.Prepare(`INSERT INTO sales SELECT orderID, contract, state, read, timestamp, total, thumbnail, buyerID, buyerHandle, title, shippingName, shippingAddress, paymentAddr, funded, transactions FROM temp_sales;`)
	if err != nil {
		return err
	}
	defer stmt3.Close()
	_, err = stmt3.Exec()
	if err != nil {
		tx.Rollback()
		return err
	}
	stmt4, err := tx.Prepare(`DROP TABLE temp_sales;`)
	if err != nil {
		return err
	}
	defer stmt4.Close()
	_, err = stmt4.Exec()
	if err != nil {
		tx.Rollback()
		return err
	}
	tx.Commit()
	f1, err := os.Create(path.Join(repoPath, "repover"))
	if err != nil {
		return err
	}
	_, err = f1.Write([]byte("8"))
	if err != nil {
		return err
	}
	f1.Close()
	return nil
}
