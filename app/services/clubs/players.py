from dataclasses import dataclass

from app.services.base import TransfermarktBase
from app.utils.regex import REGEX_DOB
from app.utils.utils import extract_from_url, safe_regex
from app.utils.xpath import Clubs


@dataclass
class TransfermarktClubPlayers(TransfermarktBase):
    """
    A class for retrieving and parsing the players of a football club from Transfermarkt.

    Args:
        club_id (str): The unique identifier of the football club.
        season_id (str): The unique identifier of the season.
        URL (str): The URL template for the club's players page on Transfermarkt.
    """

    club_id: str = None
    season_id: str = None
    URL: str = "https://www.transfermarkt.com/-/kader/verein/{club_id}/saison_id/{season_id}/plus/1"

    def __post_init__(self) -> None:
        """Initialize the TransfermarktClubPlayers class."""
        self.URL = self.URL.format(club_id=self.club_id, season_id=self.season_id)
        self.page = self.request_url_page()
        self.raise_exception_if_not_found(xpath=Clubs.Players.CLUB_NAME)
        self.__update_season_id()
        self.__update_past_flag()

    def __update_season_id(self):
        """Update the season ID if it's not provided by extracting it from the website."""
        if self.season_id is None:
            self.season_id = extract_from_url(self.get_text_by_xpath(Clubs.Players.CLUB_URL), "season_id")

    def __update_past_flag(self) -> None:
        """Check if the season is the current or if it's a past one and update the flag accordingly."""
        self.past = "Current club" in self.get_list_by_xpath(Clubs.Players.PAST_FLAG)

    def __parse_club_players(self) -> list[dict]:
        """
        Parse player information from the webpage and return a list of dictionaries, each representing a player.

        Returns:
            list[dict]: A list of player information dictionaries.
        """
        page_nationalities = self.page.xpath(Clubs.Players.PAGE_NATIONALITIES)
        page_players_infos = self.page.xpath(Clubs.Players.PAGE_INFOS)
        page_players_signed_from = self.page.xpath(
            Clubs.Players.Past.PAGE_SIGNED_FROM if self.past else Clubs.Players.Present.PAGE_SIGNED_FROM,
        )
        page_players_joined_on = self.page.xpath(
            Clubs.Players.Past.PAGE_JOINED_ON if self.past else Clubs.Players.Present.PAGE_JOINED_ON,
        )
        players_ids = [extract_from_url(url) for url in self.get_list_by_xpath(Clubs.Players.URLS)]
        players_names = self.get_list_by_xpath(Clubs.Players.NAMES)
        players_positions = self.get_list_by_xpath(Clubs.Players.POSITIONS)
        
        # Detect if this is a national team (no posrela structure)
        is_national_team = len(self.page.xpath(Clubs.Players.PAGE_INFOS)) == 0 and len(players_names) > 0
        
        # Handle national teams: extract data from rows directly
        if is_national_team:
            # Get all player rows (may contain duplicates for home/away)
            all_player_rows = self.page.xpath(
                "//div[@id='yw1']//tbody//tr[.//td[@class='hauptlink']//a[contains(@href, '/profil/spieler')]]"
            )
            
            # Extract data from rows, matching with player URLs to avoid duplicates
            players_positions = []
            players_dobs_raw = []
            seen_urls = set()
            
            for url in self.get_list_by_xpath(Clubs.Players.URLS):
                # Skip if we've already processed this URL
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Find first row containing this player URL
                for row in all_player_rows:
                    row_urls = row.xpath(".//td[@class='hauptlink']//a[contains(@href, '/profil/spieler')]/@href")
                    if url in row_urls:
                        tds = row.xpath(".//td")
                        # Position is in TD[4] for national teams
                        if len(tds) > 4:
                            pos_text = "".join(tds[4].xpath(".//text()")).strip()
                            players_positions.append(pos_text if pos_text else None)
                        else:
                            players_positions.append(None)
                        
                        # DOB/Age is in TD[5] for national teams
                        if len(tds) > 5:
                            dob_text = "".join(tds[5].xpath(".//text()")).strip()
                            players_dobs_raw.append(dob_text if dob_text else None)
                        else:
                            players_dobs_raw.append(None)
                        break
                else:
                    # URL not found in any row
                    players_positions.append(None)
                    players_dobs_raw.append(None)
            
            players_dobs = [safe_regex(dob_age, REGEX_DOB, "dob") for dob_age in players_dobs_raw]
            players_ages = [safe_regex(dob_age, REGEX_DOB, "age") for dob_age in players_dobs_raw]
        else:
            # Regular club structure
            players_dobs = [
                safe_regex(dob_age, REGEX_DOB, "dob") for dob_age in self.get_list_by_xpath(Clubs.Players.DOB_AGE)
            ]
            players_ages = [
                safe_regex(dob_age, REGEX_DOB, "age") for dob_age in self.get_list_by_xpath(Clubs.Players.DOB_AGE)
            ]
        # Ensure all lists have the same length as players_ids
        base_length = len(players_ids)
        
        players_nationalities = [nationality.xpath(Clubs.Players.NATIONALITIES) for nationality in page_nationalities]
        if len(players_nationalities) != base_length:
            players_nationalities = (players_nationalities + [[]] * base_length)[:base_length]
        
        players_current_club = (
            self.get_list_by_xpath(Clubs.Players.Past.CURRENT_CLUB) if self.past else [None] * base_length
        )
        if len(players_current_club) != base_length:
            players_current_club = (players_current_club + [None] * base_length)[:base_length]
        
        players_heights = self.get_list_by_xpath(
            Clubs.Players.Past.HEIGHTS if self.past else Clubs.Players.Present.HEIGHTS,
        )
        if len(players_heights) != base_length:
            players_heights = (players_heights + [None] * base_length)[:base_length]
        
        players_foots = self.get_list_by_xpath(
            Clubs.Players.Past.FOOTS if self.past else Clubs.Players.Present.FOOTS,
            remove_empty=False,
        )
        if len(players_foots) != base_length:
            players_foots = (players_foots + [None] * base_length)[:base_length]
        
        players_joined_on = ["; ".join(e.xpath(Clubs.Players.JOINED_ON)) for e in page_players_joined_on]
        if len(players_joined_on) != base_length:
            players_joined_on = (players_joined_on + [None] * base_length)[:base_length]
        
        players_joined = ["; ".join(e.xpath(Clubs.Players.JOINED)) for e in page_players_infos]
        if len(players_joined) != base_length:
            players_joined = (players_joined + [None] * base_length)[:base_length]
        
        players_signed_from = ["; ".join(e.xpath(Clubs.Players.SIGNED_FROM)) for e in page_players_signed_from]
        if len(players_signed_from) != base_length:
            players_signed_from = (players_signed_from + [None] * base_length)[:base_length]
        
        players_contracts = (
            [None] * base_length if self.past else self.get_list_by_xpath(Clubs.Players.Present.CONTRACTS)
        )
        if len(players_contracts) != base_length:
            players_contracts = (players_contracts + [None] * base_length)[:base_length]
        
        players_marketvalues = self.get_list_by_xpath(Clubs.Players.MARKET_VALUES)
        if len(players_marketvalues) != base_length:
            players_marketvalues = (players_marketvalues + [None] * base_length)[:base_length]
        
        players_statuses = ["; ".join(e.xpath(Clubs.Players.STATUSES)) for e in page_players_infos if e is not None]
        if len(players_statuses) != base_length:
            players_statuses = (players_statuses + [""] * base_length)[:base_length]

        return [
            {
                "id": idx,
                "name": name,
                "position": position,
                "dateOfBirth": dob,
                "age": age,
                "nationality": nationality,
                "currentClub": current_club,
                "height": height,
                "foot": foot,
                "joinedOn": joined_on,
                "joined": joined,
                "signedFrom": signed_from,
                "contract": contract,
                "marketValue": market_value,
                "status": status,
            }
            for idx, name, position, dob, age, nationality, current_club, height, foot, joined_on, joined, signed_from, contract, market_value, status, in zip(  # noqa: E501
                players_ids,
                players_names,
                players_positions,
                players_dobs,
                players_ages,
                players_nationalities,
                players_current_club,
                players_heights,
                players_foots,
                players_joined_on,
                players_joined,
                players_signed_from,
                players_contracts,
                players_marketvalues,
                players_statuses,
            )
        ]

    def get_club_players(self) -> dict:
        """
        Retrieve and parse player information for the specified football club.

        Returns:
            dict: A dictionary containing the club's unique identifier, player information, and the timestamp of when
                  the data was last updated.
        """
        self.response["id"] = self.club_id
        self.response["players"] = self.__parse_club_players()

        return self.response
