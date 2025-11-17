
CREATE SCHEMA IF NOT EXISTS supplemented;

CREATE TABLE IF NOT EXISTS supplemented.agency (LIKE public.agency INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.stops (LIKE public.stops INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.routes (LIKE public.routes INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.calendar (LIKE public.calendar INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.calendar_dates (LIKE public.calendar_dates INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.shapes (LIKE public.shapes INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.trips (LIKE public.trips INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.stop_times (LIKE public.stop_times INCLUDING ALL);
CREATE TABLE IF NOT EXISTS supplemented.transfers (LIKE public.transfers INCLUDING ALL);
