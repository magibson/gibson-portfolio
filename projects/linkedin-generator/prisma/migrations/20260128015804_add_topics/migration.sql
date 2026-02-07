-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_UserSettings" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "postsPerBatch" INTEGER NOT NULL DEFAULT 5,
    "batchCount" INTEGER NOT NULL DEFAULT 1,
    "postLength" TEXT NOT NULL DEFAULT 'medium',
    "emailAddress" TEXT,
    "sourceWebsites" TEXT NOT NULL DEFAULT '[]',
    "topics" TEXT NOT NULL DEFAULT '[]',
    "schedules" TEXT NOT NULL DEFAULT '[]',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "UserSettings_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_UserSettings" ("batchCount", "createdAt", "emailAddress", "id", "postLength", "postsPerBatch", "schedules", "sourceWebsites", "updatedAt", "userId") SELECT "batchCount", "createdAt", "emailAddress", "id", "postLength", "postsPerBatch", "schedules", "sourceWebsites", "updatedAt", "userId" FROM "UserSettings";
DROP TABLE "UserSettings";
ALTER TABLE "new_UserSettings" RENAME TO "UserSettings";
CREATE UNIQUE INDEX "UserSettings_userId_key" ON "UserSettings"("userId");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
