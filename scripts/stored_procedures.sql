-- Stored Procedure for Active Users Count
CREATE OR REPLACE PROCEDURE get_active_users_count()
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY SELECT COUNT(*) FROM usuarios WHERE activo = TRUE;
END;
$$;

-- Stored Procedure for Revenue by Localities
CREATE OR REPLACE PROCEDURE get_revenue_by_localities()
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT l.nombre AS localidad, SUM(tf.valor) AS total_recaudado
    FROM viajes v
    JOIN tarifas tf ON v.tarifa_id = tf.tarifa_id
    JOIN localidades l ON v.localidad_id = l.localidad_id
    GROUP BY l.nombre;
END;
$$;