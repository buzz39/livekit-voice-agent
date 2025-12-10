import { Pool } from '@neondatabase/serverless';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    const { url, table, row } = await request.json();

    if (!url || !table || !row) {
        return NextResponse.json(
            { error: 'Database URL, table name, and row data required' },
            { status: 400 }
        );
    }

    let client;
    try {
        const pool = new Pool({ connectionString: url });
        client = await pool.connect();

        // Get primary keys for the table
        const pkQuery = `
            SELECT column_name 
            FROM information_schema.key_column_usage 
            WHERE table_schema = 'public' AND table_name = $1 AND constraint_name LIKE '%pkey%'
        `;
        const pkResult = await client.query(pkQuery, [table]);
        const pkColumns = pkResult.rows.map((row: any) => row.column_name);

        // Build UPDATE or INSERT query
        const columns = Object.keys(row);
        const values = Object.values(row);
        const placeholders = columns.map((_, i) => `$${i + 1}`).join(', ');
        const columnsList = columns.join(', ');

        // Try to determine if this is an update or insert
        let query;
        if (pkColumns.length > 0) {
            // Use primary key for update
            const pkWhere = pkColumns
                .map((col, i) => {
                    const idx = columns.indexOf(col);
                    return `${col} = $${idx + 1}`;
                })
                .join(' AND ');

            const setClause = columns
                .map((col, i) => {
                    if (pkColumns.includes(col)) return null;
                    return `${col} = $${i + 1}`;
                })
                .filter(Boolean)
                .join(', ');

            if (setClause) {
                query = `UPDATE ${table} SET ${setClause} WHERE ${pkWhere}`;
                await client.query(query, values);
            } else {
                // No non-PK columns to update, just ensure it exists
                query = `INSERT INTO ${table} (${columnsList}) VALUES (${placeholders}) ON CONFLICT DO NOTHING`;
                await client.query(query, values);
            }
        } else {
            // No PK, try insert
            query = `INSERT INTO ${table} (${columnsList}) VALUES (${placeholders}) ON CONFLICT DO NOTHING`;
            await client.query(query, values);
        }

        await client.release();
        return NextResponse.json({ success: true }, { status: 200 });
    } catch (error: any) {
        return NextResponse.json(
            { error: error.message || 'Failed to update row' },
            { status: 500 }
        );
    } finally {
        if (client) {
            try {
                await client.release();
            } catch (e) {
                // Ignore release errors
            }
        }
    }
}
