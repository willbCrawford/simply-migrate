ALTER TABLE customers
    ADD COLUMN address_id INTEGER REFERENCES addresses(id);