-- Función wrapper INMUTABLE para text search en inglés
CREATE OR REPLACE FUNCTION text_to_tsvector_english(input_text TEXT)
RETURNS TSVECTOR AS $$
    SELECT to_tsvector('english', COALESCE(input_text, ''));
$$ LANGUAGE sql IMMUTABLE;
