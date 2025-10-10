--
-- PostgreSQL database dump
--

\restrict tOTZ625cj3ogWEpQKfPC8h2g38OfTdof1xQLuI9R4M3kTg7bBeUehvRCJ0KhLNH

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cards; Type: TABLE; Schema: public; Owner: beer_user
--

CREATE TABLE public.cards (
    card_uid character varying(50) NOT NULL,
    guest_id uuid NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cards OWNER TO beer_user;

--
-- Name: guests; Type: TABLE; Schema: public; Owner: beer_user
--

CREATE TABLE public.guests (
    guest_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    last_name character varying(50) NOT NULL,
    first_name character varying(50) NOT NULL,
    patronymic character varying(50),
    phone_number character varying(20) NOT NULL,
    date_of_birth date NOT NULL,
    id_document character varying(100) NOT NULL,
    balance numeric(10,2) DEFAULT 0.00 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.guests OWNER TO beer_user;

--
-- Name: kegs; Type: TABLE; Schema: public; Owner: beer_user
--

CREATE TABLE public.kegs (
    keg_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    beer_name character varying(100) NOT NULL,
    brewery character varying(100),
    beer_style character varying(50),
    abv numeric(4,2),
    initial_volume_ml integer NOT NULL,
    current_volume_ml integer NOT NULL,
    purchase_price numeric(10,2),
    tapped_at timestamp with time zone,
    finished_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.kegs OWNER TO beer_user;

--
-- Name: pours; Type: TABLE; Schema: public; Owner: beer_user
--

CREATE TABLE public.pours (
    pour_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    guest_id uuid NOT NULL,
    card_uid character varying(50) NOT NULL,
    tap_id integer NOT NULL,
    keg_id uuid NOT NULL,
    client_tx_id character varying(100) NOT NULL,
    volume_ml integer NOT NULL,
    price_per_ml_at_pour numeric(10,4) NOT NULL,
    amount_charged numeric(10,2) NOT NULL,
    poured_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.pours OWNER TO beer_user;

--
-- Name: taps; Type: TABLE; Schema: public; Owner: beer_user
--

CREATE TABLE public.taps (
    tap_id integer NOT NULL,
    keg_id uuid,
    display_name character varying(50) NOT NULL,
    price_per_ml numeric(10,4) NOT NULL,
    last_cleaned_at timestamp with time zone
);


ALTER TABLE public.taps OWNER TO beer_user;

--
-- Name: taps_tap_id_seq; Type: SEQUENCE; Schema: public; Owner: beer_user
--

CREATE SEQUENCE public.taps_tap_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.taps_tap_id_seq OWNER TO beer_user;

--
-- Name: taps_tap_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: beer_user
--

ALTER SEQUENCE public.taps_tap_id_seq OWNED BY public.taps.tap_id;


--
-- Name: taps tap_id; Type: DEFAULT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.taps ALTER COLUMN tap_id SET DEFAULT nextval('public.taps_tap_id_seq'::regclass);


--
-- Data for Name: cards; Type: TABLE DATA; Schema: public; Owner: beer_user
--

COPY public.cards (card_uid, guest_id, status, created_at) FROM stdin;
\.


--
-- Data for Name: guests; Type: TABLE DATA; Schema: public; Owner: beer_user
--

COPY public.guests (guest_id, last_name, first_name, patronymic, phone_number, date_of_birth, id_document, balance, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: kegs; Type: TABLE DATA; Schema: public; Owner: beer_user
--

COPY public.kegs (keg_id, beer_name, brewery, beer_style, abv, initial_volume_ml, current_volume_ml, purchase_price, tapped_at, finished_at, created_at) FROM stdin;
85829b4e-5e6f-4998-818b-e6df0a11f910	Classic Lager	Local Brewery	Lager	4.50	30000	30000	7500.00	2025-10-10 10:02:47.706189+00	\N	2025-10-10 10:02:47.706189+00
03b1502a-aaa7-44d4-8061-836c42ea5819	Dark Stout	Craft Beer Masters	Stout	6.20	30000	30000	9000.00	2025-10-10 10:02:47.706189+00	\N	2025-10-10 10:02:47.706189+00
4e0c12f1-6fa5-4e7c-b875-4b1a1edfe7dc	Cosmic Haze IPA	Galaxy Brews	IPA	6.80	30000	30000	9800.00	2025-10-10 10:02:47.706189+00	\N	2025-10-10 10:02:47.706189+00
\.


--
-- Data for Name: pours; Type: TABLE DATA; Schema: public; Owner: beer_user
--

COPY public.pours (pour_id, guest_id, card_uid, tap_id, keg_id, client_tx_id, volume_ml, price_per_ml_at_pour, amount_charged, poured_at, created_at) FROM stdin;
\.


--
-- Data for Name: taps; Type: TABLE DATA; Schema: public; Owner: beer_user
--

COPY public.taps (tap_id, keg_id, display_name, price_per_ml, last_cleaned_at) FROM stdin;
1	85829b4e-5e6f-4998-818b-e6df0a11f910	Kran #1	0.5000	2025-10-10 10:02:47.706189+00
2	03b1502a-aaa7-44d4-8061-836c42ea5819	Kran #2	0.6500	2025-10-10 10:02:47.706189+00
3	4e0c12f1-6fa5-4e7c-b875-4b1a1edfe7dc	Kran #3	0.7500	2025-10-10 10:02:47.706189+00
\.


--
-- Name: taps_tap_id_seq; Type: SEQUENCE SET; Schema: public; Owner: beer_user
--

SELECT pg_catalog.setval('public.taps_tap_id_seq', 3, true);


--
-- Name: cards cards_pkey; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.cards
    ADD CONSTRAINT cards_pkey PRIMARY KEY (card_uid);


--
-- Name: guests guests_id_document_key; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.guests
    ADD CONSTRAINT guests_id_document_key UNIQUE (id_document);


--
-- Name: guests guests_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.guests
    ADD CONSTRAINT guests_phone_number_key UNIQUE (phone_number);


--
-- Name: guests guests_pkey; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.guests
    ADD CONSTRAINT guests_pkey PRIMARY KEY (guest_id);


--
-- Name: kegs kegs_pkey; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.kegs
    ADD CONSTRAINT kegs_pkey PRIMARY KEY (keg_id);


--
-- Name: pours pours_client_tx_id_key; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.pours
    ADD CONSTRAINT pours_client_tx_id_key UNIQUE (client_tx_id);


--
-- Name: pours pours_pkey; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.pours
    ADD CONSTRAINT pours_pkey PRIMARY KEY (pour_id);


--
-- Name: taps taps_pkey; Type: CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.taps
    ADD CONSTRAINT taps_pkey PRIMARY KEY (tap_id);


--
-- Name: idx_cards_guest_id; Type: INDEX; Schema: public; Owner: beer_user
--

CREATE INDEX idx_cards_guest_id ON public.cards USING btree (guest_id);


--
-- Name: idx_pours_client_tx_id; Type: INDEX; Schema: public; Owner: beer_user
--

CREATE INDEX idx_pours_client_tx_id ON public.pours USING btree (client_tx_id);


--
-- Name: idx_pours_guest_id; Type: INDEX; Schema: public; Owner: beer_user
--

CREATE INDEX idx_pours_guest_id ON public.pours USING btree (guest_id);


--
-- Name: idx_pours_tap_id; Type: INDEX; Schema: public; Owner: beer_user
--

CREATE INDEX idx_pours_tap_id ON public.pours USING btree (tap_id);


--
-- Name: pours fk_card; Type: FK CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.pours
    ADD CONSTRAINT fk_card FOREIGN KEY (card_uid) REFERENCES public.cards(card_uid);


--
-- Name: cards fk_guest; Type: FK CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.cards
    ADD CONSTRAINT fk_guest FOREIGN KEY (guest_id) REFERENCES public.guests(guest_id) ON DELETE CASCADE;


--
-- Name: pours fk_guest; Type: FK CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.pours
    ADD CONSTRAINT fk_guest FOREIGN KEY (guest_id) REFERENCES public.guests(guest_id);


--
-- Name: taps fk_keg; Type: FK CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.taps
    ADD CONSTRAINT fk_keg FOREIGN KEY (keg_id) REFERENCES public.kegs(keg_id) ON DELETE SET NULL;


--
-- Name: pours fk_keg; Type: FK CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.pours
    ADD CONSTRAINT fk_keg FOREIGN KEY (keg_id) REFERENCES public.kegs(keg_id);


--
-- Name: pours fk_tap; Type: FK CONSTRAINT; Schema: public; Owner: beer_user
--

ALTER TABLE ONLY public.pours
    ADD CONSTRAINT fk_tap FOREIGN KEY (tap_id) REFERENCES public.taps(tap_id);


--
-- PostgreSQL database dump complete
--

\unrestrict tOTZ625cj3ogWEpQKfPC8h2g38OfTdof1xQLuI9R4M3kTg7bBeUehvRCJ0KhLNH

