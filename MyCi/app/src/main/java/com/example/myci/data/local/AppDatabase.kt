package com.example.myci.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        LoanApplicationEntity::class,
        DocumentEntity::class,
        MemberEntity::class,
        PendingOpEntity::class
    ],
    version = 3,
    exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun loanApplicationDao(): LoanApplicationDao
    abstract fun documentDao(): DocumentDao
    abstract fun memberDao(): MemberDao
    abstract fun pendingOpDao(): PendingOpDao

    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null

        fun get(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val db = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "myci.db"
                )
                    // Replace with proper migrations once schemas evolve.
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = db
                db
            }
        }
    }
}
