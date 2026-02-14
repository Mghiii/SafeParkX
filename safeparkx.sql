-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : 127.0.0.1
-- Généré le : lun. 21 juil. 2025 à 00:18
-- Version du serveur : 10.4.32-MariaDB
-- Version de PHP : 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de données : `safeparkx`
--

-- --------------------------------------------------------

--
-- Structure de la table `admin`
--

CREATE TABLE `admin` (
  `id` int(11) NOT NULL,
  `nom` varchar(50) DEFAULT NULL,
  `prenom` varchar(50) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `admin`
--

INSERT INTO `admin` (`id`, `nom`, `prenom`, `email`, `password`) VALUES
(1, 'admin', 'admin', 'admin@admin', 'admin');

-- --------------------------------------------------------

--
-- Structure de la table `places`
--

CREATE TABLE `places` (
  `id_place` int(11) NOT NULL,
  `id_ticket` int(11) DEFAULT NULL,
  `id_admin` int(11) DEFAULT NULL,
  `etat` tinyint(1) DEFAULT NULL,
  `id_vehicule` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `places`
--

INSERT INTO `places` (`id_place`, `id_ticket`, `id_admin`, `etat`, `id_vehicule`) VALUES
(1, 3, 1, 1, 1),
(2, 4, 1, 1, 2),
(3, 5, 1, 1, 3),
(4, 6, 1, 1, 4),
(5, 7, 1, 1, 5),
(6, 8, 1, 1, 6),
(7, 9, 1, 1, 7),
(8, 10, 1, 1, 8),
(9, 11, 1, 1, 9),
(10, 12, 1, 1, 10),
(11, 13, 1, 1, 11),
(12, 14, 1, 1, 12),
(13, NULL, 1, 0, NULL),
(14, NULL, 1, 0, NULL),
(15, NULL, 1, 0, NULL),
(16, NULL, 1, 0, NULL),
(17, NULL, 1, 0, NULL),
(18, NULL, 1, 0, NULL),
(19, NULL, 1, 0, NULL),
(20, NULL, 1, 0, NULL);

-- --------------------------------------------------------

--
-- Structure de la table `ticket`
--

CREATE TABLE `ticket` (
  `id_ticket` int(11) NOT NULL,
  `id_place` int(11) DEFAULT NULL,
  `id_vehicule` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `ticket`
--

INSERT INTO `ticket` (`id_ticket`, `id_place`, `id_vehicule`) VALUES
(3, 1, 1),
(4, 2, 2),
(5, 3, 3),
(6, 4, 4),
(7, 5, 5),
(8, 6, 6),
(9, 7, 7),
(10, 8, 8),
(11, 9, 9),
(12, 10, 10),
(13, 11, 11),
(14, 12, 12);

-- --------------------------------------------------------

--
-- Structure de la table `vehicule`
--

CREATE TABLE `vehicule` (
  `id_vehicule` int(11) NOT NULL,
  `id_admin` int(11) DEFAULT NULL,
  `id_ticket` int(11) DEFAULT NULL,
  `matricule` varchar(50) DEFAULT NULL,
  `type_vehicule` varchar(50) DEFAULT NULL,
  `date_entrer` date DEFAULT NULL,
  `date_sortie` date DEFAULT NULL,
  `id_place` int(11) DEFAULT NULL,
  `image_path` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `vehicule`
--

INSERT INTO `vehicule` (`id_vehicule`, `id_admin`, `id_ticket`, `matricule`, `type_vehicule`, `date_entrer`, `date_sortie`, `id_place`) VALUES
(1, 1, NULL, 'XY789AB', 'Voiture', '2025-07-19', NULL, 1),
(2, 1, NULL, 'XY789BB', 'Voiture', '2025-07-19', NULL, 2),
(3, 1, NULL, 'AB123CD', 'Voiture', '2025-07-19', NULL, 3),
(4, 1, NULL, 'EF456GH', 'Moto', '2025-07-19', NULL, 4),
(5, 1, NULL, 'IJ789KL', 'Voiture', '2025-07-19', NULL, 5),
(6, 1, NULL, 'MN012OP', 'Camion', '2025-07-19', NULL, 6),
(7, 1, NULL, 'QR345ST', 'Voiture', '2025-07-19', NULL, 7),
(8, 1, NULL, 'UV678WX', 'Moto', '2025-07-19', NULL, 8),
(9, 1, NULL, 'YZ901AB', 'Voiture', '2025-07-19', NULL, 9),
(10, 1, NULL, 'CD234EF', 'Camion', '2025-07-19', NULL, 10),
(11, 1, NULL, 'GH567IJ', 'Voiture', '2025-07-19', NULL, 11),
(12, 1, NULL, 'KL890MN', 'Moto', '2025-07-19', NULL, 12);

--
-- Déclencheurs `vehicule`
--
DELIMITER $$
CREATE TRIGGER `after_vehicule_insert` AFTER INSERT ON `vehicule` FOR EACH ROW BEGIN
    DECLARE place_id INT;
    
    -- Trouver une place libre (etat = 0)
    SELECT id_place INTO place_id 
    FROM places 
    WHERE etat = 0 
    LIMIT 1;
    
    -- Si une place libre est trouvée
    IF place_id IS NOT NULL THEN
        -- Mettre à jour la place (la rendre occupée)
        UPDATE places 
        SET etat = 1, 
            id_vehicule = NEW.id_vehicule,
            id_admin = NEW.id_admin 
        WHERE id_place = place_id;
        
        -- Mettre à jour le véhicule avec l'id_place
        UPDATE vehicule 
        SET id_place = place_id 
        WHERE id_vehicule = NEW.id_vehicule;
    END IF;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `after_vehicule_update` AFTER UPDATE ON `vehicule` FOR EACH ROW BEGIN
    -- Si la date de sortie a été ajoutée (le véhicule sort)
    IF NEW.date_sortie IS NOT NULL AND OLD.date_sortie IS NULL THEN
        -- Libérer la place associée
        UPDATE places 
        SET etat = 0, 
            id_vehicule = NULL, 
            id_admin = NULL 
        WHERE id_place = NEW.id_place;
    END IF;
END
$$
DELIMITER ;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `admin`
--
ALTER TABLE `admin`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Index pour la table `places`
--
ALTER TABLE `places`
  ADD PRIMARY KEY (`id_place`),
  ADD KEY `fk_places_ticket` (`id_ticket`),
  ADD KEY `fk_places_admin` (`id_admin`),
  ADD KEY `fk_places_vehicule` (`id_vehicule`);

--
-- Index pour la table `ticket`
--
ALTER TABLE `ticket`
  ADD PRIMARY KEY (`id_ticket`),
  ADD KEY `fk_ticket_place` (`id_place`),
  ADD KEY `fk_ticket_vehicule` (`id_vehicule`);

--
-- Index pour la table `vehicule`
--
ALTER TABLE `vehicule`
  ADD PRIMARY KEY (`id_vehicule`),
  ADD UNIQUE KEY `matricule` (`matricule`),
  ADD KEY `fk_vehicule_admin` (`id_admin`),
  ADD KEY `fk_vehicule_ticket` (`id_ticket`),
  ADD KEY `fk_vehicule_place` (`id_place`);

--
-- AUTO_INCREMENT pour les tables déchargées
--

--
-- AUTO_INCREMENT pour la table `admin`
--
ALTER TABLE `admin`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT pour la table `places`
--
ALTER TABLE `places`
  MODIFY `id_place` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT pour la table `ticket`
--
ALTER TABLE `ticket`
  MODIFY `id_ticket` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT pour la table `vehicule`
--
ALTER TABLE `vehicule`
  MODIFY `id_vehicule` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `places`
--
ALTER TABLE `places`
  ADD CONSTRAINT `fk_places_admin` FOREIGN KEY (`id_admin`) REFERENCES `admin` (`id`),
  ADD CONSTRAINT `fk_places_ticket` FOREIGN KEY (`id_ticket`) REFERENCES `ticket` (`id_ticket`),
  ADD CONSTRAINT `fk_places_vehicule` FOREIGN KEY (`id_vehicule`) REFERENCES `vehicule` (`id_vehicule`);

--
-- Contraintes pour la table `ticket`
--
ALTER TABLE `ticket`
  ADD CONSTRAINT `fk_ticket_place` FOREIGN KEY (`id_place`) REFERENCES `places` (`id_place`),
  ADD CONSTRAINT `fk_ticket_vehicule` FOREIGN KEY (`id_vehicule`) REFERENCES `vehicule` (`id_vehicule`);

--
-- Contraintes pour la table `vehicule`
--
ALTER TABLE `vehicule`
  ADD CONSTRAINT `fk_vehicule_admin` FOREIGN KEY (`id_admin`) REFERENCES `admin` (`id`),
  ADD CONSTRAINT `fk_vehicule_place` FOREIGN KEY (`id_place`) REFERENCES `places` (`id_place`),
  ADD CONSTRAINT `fk_vehicule_ticket` FOREIGN KEY (`id_ticket`) REFERENCES `ticket` (`id_ticket`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
