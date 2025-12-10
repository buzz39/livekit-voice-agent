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

        if (pkColumns.length === 0) {
            return NextResponse.json(
                { error: 'Table does not have a primary key' },
                { status: 400 }
            );
        }

        // Build WHERE clause from primary keys
        const whereConditions = pkColumns
            .map((col, i) => {
                const value = row[col];
                if (value === null || value === undefined) {
                    return `${col} IS NULL`;
                }
                return `${col} = ${typeof value === 'string' ? `'${value.replace(/'/g, "''")}'` : value}`;
            })
            .join(' AND ');

        const deleteQuery = `DELETE FROM ${table} WHERE ${whereConditions}`;
        await client.query(deleteQuery);

        await client.release();
        return NextResponse.json({ success: true }, { status: 200 });
    } catch (error: any) {
        return NextResponse.json(
            { error: error.message || 'Failed to delete row' },
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
